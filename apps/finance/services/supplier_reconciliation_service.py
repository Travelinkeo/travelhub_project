import logging
from decimal import Decimal

import pandas as pd
from django.db.models import Q
from pydantic import BaseModel, Field

# resolved dynamically to avoid circular dependencies
from apps.bookings.models import ItemVenta

logger = logging.getLogger(__name__)


# Esquemas de extracción para la IA
class LineaLiquidacionSchema(BaseModel):
    locator: str = Field(description="El localizador, PNR o ID de reserva/boleto")
    amount: float = Field(description="El costo neto o monto a pagar/cobrado por el proveedor")
    passenger: str | None = Field(None, description="Nombre del pasajero, si aparece")


class LiquidacionProveedorSchema(BaseModel):
    lineas: list[LineaLiquidacionSchema] = Field(
        description="Lista de servicios o boletos cobrados"
    )


class SupplierReconciliationService:
    """
    Servicio para conciliar reportes de proveedores con las ventas internas.
    Soporta Excel y PDF (vía IA).
    """

    def __init__(self, agencia=None):
        self.agencia = agencia

    def reconcile_from_excel(self, excel_file, provider_id):
        """
        Lee un Excel de proveedor y busca discrepancias.
        """
        try:
            df = pd.read_excel(excel_file)
            # Normalizar columnas
            results = []

            for _, row in df.iterrows():
                locator = str(row.get("Locator", row.get("PNR", row.get("Booking ID", "")))).strip()
                provider_cost = Decimal(
                    str(row.get("Net", row.get("Cost", row.get("Amount", 0)))) or "0"
                )

                if not locator or locator == "nan":
                    continue

                # Buscar en nuestra base de datos
                query = Q(codigo_reserva_proveedor__iexact=locator)
                if self.agencia:
                    query &= Q(venta__agencia=self.agencia)

                item = ItemVenta.objects.filter(query).first()

                status = "OK"
                diff = Decimal("0.00")
                internal_cost = Decimal("0.00")

                if not item:
                    status = "NOT_FOUND_INTERNALLY"
                else:
                    internal_cost = item.costo_neto_proveedor or Decimal("0.00")
                    diff = provider_cost - internal_cost
                    if abs(diff) > 0.01:
                        status = "DISCREPANCY"

                results.append(
                    {
                        "locator": locator,
                        "provider_cost": provider_cost,
                        "internal_cost": internal_cost,
                        "difference": diff,
                        "status": status,
                        "item_id": item.id_item_venta if item else None,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error en conciliación Excel: {e}")
            return None

    def reconcile_from_pdf_ia(self, file_obj, filename, provider_id=None):
        """
        Usa Gemini para extraer la tabla de un PDF de proveedor y luego concilia.
        """
        try:
            from django.utils.module_loading import import_string
            ExtractionService = import_string("apps.automation.parsers.extraction.ExtractionService")
            ai_engine = import_string("apps.automation.services.ai_engine.ai_engine")

            # 1. Extraer texto del PDF
            text = ExtractionService.extract_text(file_obj, filename)
            if not text:
                logger.error("No se pudo extraer texto del PDF de liquidación.")
                return None

            # 2. Enviar a IA para extraer el JSON estructurado
            system_prompt = (
                "Eres un auditor contable automatizado. "
                "Tu tarea es analizar reportes de liquidación de proveedores de viajes (BSP, KIU, Sabre, Amadeus) "
                "y extraer una lista estructurada de los cobros realizados por cada localizador/PNR o boleto."
            )

            res = ai_engine.parse_structured_data(
                text=f"Analiza este reporte de liquidación y extrae los servicios cobrados:\n\n{text}",
                schema=LiquidacionProveedorSchema,
                system_prompt=system_prompt,
            )

            if "error" in res:
                logger.error(f"Error de IA en conciliación PDF: {res['error']}")
                return None

            lineas_extraidas = res.get("lineas", [])

            # 3. Conciliar con nuestra base de datos (ItemVenta)
            results = []
            locators = [str(linea.get("locator", "")).strip() for linea in lineas_extraidas]
            locators = [l for l in locators if l]
            items_map = {}
            if locators:
                q = Q(codigo_reserva_proveedor__in=locators)
                if self.agencia:
                    q &= Q(venta__agencia=self.agencia)
                for item in ItemVenta.objects.filter(q).select_related("venta"):
                    items_map.setdefault(item.codigo_reserva_proveedor.upper(), item)
            for linea in lineas_extraidas:
                locator = str(linea.get("locator", "")).strip()
                provider_cost = Decimal(str(linea.get("amount", 0)))
                passenger = linea.get("passenger")

                if not locator:
                    continue

                item = items_map.get(locator.upper())

                status = "OK"
                diff = Decimal("0.00")
                internal_cost = Decimal("0.00")

                if not item:
                    status = "NOT_FOUND_INTERNALLY"
                else:
                    internal_cost = item.costo_neto_proveedor or Decimal("0.00")
                    diff = provider_cost - internal_cost
                    if abs(diff) > 0.01:
                        status = "DISCREPANCY"

                results.append(
                    {
                        "locator": locator,
                        "provider_cost": provider_cost,
                        "internal_cost": internal_cost,
                        "difference": diff,
                        "status": status,
                        "item_id": item.id_item_venta if item else None,
                        "passenger": passenger,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error en conciliación PDF IA: {e}", exc_info=True)
            return None

    def export_results_to_excel(self, results, output_stream):
        """
        Exporta los resultados de la conciliación a un archivo Excel.
        """
        if not results:
            return False

        try:
            df = pd.DataFrame(results)
            # Reorganizar y renombrar columnas para mejor lectura
            column_mapping = {
                "locator": "Localizador/PNR",
                "passenger": "Pasajero",
                "provider_cost": "Costo Proveedor",
                "internal_cost": "Costo Interno",
                "difference": "Diferencia",
                "status": "Estado",
                "item_id": "ID Item (Interno)",
            }
            # Filtrar solo las columnas que existen en los resultados
            cols_to_use = [col for col in column_mapping.keys() if col in df.columns]
            df = df[cols_to_use].rename(columns=column_mapping)

            # Exportar a excel
            df.to_excel(output_stream, index=False, engine="openpyxl")
            return True
        except Exception as e:
            logger.error(f"Error exportando conciliación a Excel: {e}", exc_info=True)
            return False

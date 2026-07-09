import logging
from decimal import Decimal
import csv
from io import StringIO

from apps.finance.models.facturas_proveedores import FacturaProveedor

logger = logging.getLogger(__name__)

class LibroComprasService:
    """
    Servicio para generar Libro de Compras según normativa SENIAT
    """

    @staticmethod
    def generar_libro_compras(fecha_inicio, fecha_fin, agencia=None):
        """
        Genera el libro de compras para un período

        Args:
            fecha_inicio: date - Fecha inicial del período
            fecha_fin: date - Fecha final del período
            agencia: Agencia - Filtrar por agencia (opcional)

        Returns:
            dict con estructura del libro de compras
        """
        # Filtrar facturas de proveedores del período
        facturas = (
            FacturaProveedor.objects.filter(
                fecha_emision__gte=fecha_inicio,
                fecha_emision__lte=fecha_fin,
                estado=FacturaProveedor.EstadoFactura.CONCILIADA,
            )
            .select_related("proveedor", "moneda")
            .order_by("fecha_emision", "numero_factura")
        )

        if agencia:
            facturas = facturas.filter(agencia=agencia)

        compras = []
        totales = {
            "base_gravada": Decimal("0.00"),
            "base_exenta": Decimal("0.00"),
            "iva_16": Decimal("0.00"),
            "total": Decimal("0.00"),
        }

        for f in facturas:
            datos = f.datos_json or {}
            
            # Obtener base y iva de los datos extraídos por IA
            try:
                base_gravada = Decimal(str(datos.get("base_gravada", "0.00")))
            except Exception:
                base_gravada = Decimal("0.00")
            
            try:
                iva = Decimal(str(datos.get("iva", "0.00")))
            except Exception:
                iva = Decimal("0.00")

            if base_gravada == 0 and iva == 0:
                # Por defecto asumimos exento para aerolíneas/tiquetes de viaje
                base_exenta = f.monto_total
            else:
                base_exenta = f.monto_total - (base_gravada + iva)
                if base_exenta < 0:
                    base_exenta = Decimal("0.00")

            proveedor_rif = datos.get("proveedor_rif") or (f.proveedor.rif if f.proveedor else "")

            registro = {
                "fecha": f.fecha_emision,
                "numero_factura": f.numero_factura,
                "proveedor_rif": proveedor_rif,
                "proveedor_nombre": f.proveedor_nombre,
                "base_gravada": base_gravada,
                "base_exenta": base_exenta,
                "iva_16": iva,
                "total": f.monto_total,
            }
            compras.append(registro)

            totales["base_gravada"] += base_gravada
            totales["base_exenta"] += base_exenta
            totales["iva_16"] += iva
            totales["total"] += f.monto_total

        return {
            "periodo": {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            },
            "compras": compras,
            "totales": totales,
            "resumen": {
                "total_facturas": len(compras),
                "credito_fiscal": totales["iva_16"],
            },
        }

    @staticmethod
    def exportar_csv(libro_compras) -> str:
        """
        Exporta el libro de compras a formato CSV

        Args:
            libro_compras: dict - Resultado de generar_libro_compras()

        Returns:
            str - Contenido CSV
        """
        output = StringIO()
        writer = csv.writer(output, delimiter=";")

        # Encabezado
        writer.writerow([
            "Fecha",
            "Número Factura",
            "RIF Proveedor",
            "Nombre Proveedor",
            "Base Gravada",
            "Base Exenta",
            "IVA (Impuesto)",
            "Total"
        ])

        for c in libro_compras["compras"]:
            writer.writerow([
                c["fecha"].strftime("%Y-%m-%d"),
                c["numero_factura"],
                c["proveedor_rif"],
                c["proveedor_nombre"],
                f"{c['base_gravada']:.2f}",
                f"{c['base_exenta']:.2f}",
                f"{c['iva_16']:.2f}",
                f"{c['total']:.2f}"
            ])

        # Totales
        writer.writerow([])
        writer.writerow([
            "TOTALES",
            "",
            "",
            "",
            f"{libro_compras['totales']['base_gravada']:.2f}",
            f"{libro_compras['totales']['base_exenta']:.2f}",
            f"{libro_compras['totales']['iva_16']:.2f}",
            f"{libro_compras['totales']['total']:.2f}"
        ])

        return output.getvalue()

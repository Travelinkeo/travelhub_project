import datetime as dt
import logging
from typing import Any

from django.template.loader import render_to_string

from apps.common.services.pdf_renderer import PdfRendererService

logger = logging.getLogger(__name__)


class PdfGenerationService:
    """
    Renderiza boletos en PDF A4 usando WeasyPrint (local).
    """

    @staticmethod
    def generate_ticket(
        data: dict[str, Any], agencia_obj=None, boleto_obj=None, **kwargs
    ) -> tuple[bytes, str]:
        """
        Genera el PDF del boleto usando la plantilla unificada y WeasyPrint.
        """
        try:
            # Selección de plantilla
            source_system = data.get("SOURCE_SYSTEM", "KIU").upper()
            template_name = "core/tickets/golden_ticket_v2.html"

            # Inyección de contexto
            context = PdfGenerationService._build_context(
                data, agencia_obj, source_system, boleto_obj=boleto_obj
            )

            # Renderizado HTML
            html_out = render_to_string(template_name, context)

            # --- RENDERIZADO DE PDF (WeasyPrint) ---
            logger.info(f" Generando PDF para PNR: {context.get('CODIGO_RESERVA')}")
            pdf_bytes = PdfRendererService.render_html_to_pdf(html_out)

            # Nombre de archivo profesional
            num_boleto = (
                data.get("NUMERO_DE_BOLETO")
                or data.get("ticket_number")
                or data.get("numero_boleto")
                or (boleto_obj.numero_boleto if boleto_obj else None)
                or "S-N"
            )

            import re

            nombre_pasajero = context.get("NOMBRE_DEL_PASAJERO", "PASAJERO")
            # Reemplazar caracteres especiales y espacios por guión bajo
            nombre_limpio = re.sub(r"[^A-Za-z0-9]", "_", nombre_pasajero).strip("_").upper()

            fname = f"Boleto_{num_boleto}_{nombre_limpio}.pdf"

            return pdf_bytes, fname

        except Exception as e:
            logger.error(f" Fallo crítico en generación de PDF de boleto: {e}", exc_info=True)
            return b"", "error_generacion.pdf"

    @staticmethod
    def _build_context(
        data: dict[str, Any], agencia_obj, source_system: str, boleto_obj=None
    ) -> dict:
        """
        Construye el diccionario de contexto unificado para la plantilla HTML del boleto.
        Extrae y normaliza todos los campos necesarios.
        """
        from apps.common.utils import sanitize_passenger_name

        # Sanitizar nombre de pasajero
        nombre_original = (
            data.get("NOMBRE_DEL_PASAJERO")
            or data.get("passenger_name")
            or data.get("nombre_pasajero")
            or (boleto_obj.nombre_pasajero_completo if boleto_obj else None)
            or "PASAJERO"
        )
        solo_nombre = data.get("solo_nombre_pasajero")
        nombre_original = sanitize_passenger_name(nombre_original)

        # Mutar el diccionario de entrada para retrocompatibilidad con tests y pipelines
        if "NOMBRE_DEL_PASAJERO" in data:
            data["NOMBRE_DEL_PASAJERO"] = nombre_original
        elif "passenger_name" in data:
            data["passenger_name"] = nombre_original

        if not solo_nombre:
            if "/" in nombre_original:
                parts = nombre_original.split("/")
                if len(parts) > 1:
                    full_first_name = parts[1].strip()
                    import re

                    solo_nombre = re.sub(
                        r"\s+(MR|MRS|MS|MSTR|MISS|M|F)$", "", full_first_name, flags=re.IGNORECASE
                    ).split(" ")[0]
                else:
                    solo_nombre = parts[0].strip().split(" ")[0]
            else:
                solo_nombre = nombre_original.split(" ")[0]

        # Limpieza final
        solo_nombre = str(solo_nombre).strip().upper() if solo_nombre else "VIAJERO"

        f_emision = data.get("FECHA_DE_EMISION") or data.get("fecha_emision")
        if not f_emision or str(f_emision).strip().lower() == "no encontrado":
            f_emision = dt.datetime.now().strftime("%d%b%y").upper()
            # Traducir meses a inglés si es necesario
            from core.models.ai_schemas import MESES_ES_TO_EN

            for es, en in MESES_ES_TO_EN.items():
                f_emision = f_emision.replace(es, en)
        else:
            try:
                import dateutil.parser as date_parser

                from apps.automation.parsers.normalization import GDS_NUM_TO_EN

                dt_obj = date_parser.parse(str(f_emision))
                day = dt_obj.strftime("%d")
                month = GDS_NUM_TO_EN.get(dt_obj.month, "JAN")
                year = dt_obj.strftime("%y")
                f_emision = f"{day}{month}{year}"
            except Exception as e:
                logger.warning(
                    f"No se pudo formatear fecha de emision '{f_emision}' a DDMMMAA: {e}"
                )

        agente = data.get("AGENTE_EMISOR") or data.get("agencia_nombre")
        if not agente and agencia_obj:
            agente = agencia_obj.iata or agencia_obj.nombre_comercial

        # Localizador de aerolínea (si no está al top-level, buscar en segmentos)
        loc_aero = (
            data.get("CODIGO_RESERVA_AEROLINEA")
            or data.get("airline_pnr")
            or data.get("pnr_aerolinea")
        )
        if not loc_aero:
            vuelos_data = data.get("segmentos") or data.get("vuelos") or data.get("flights") or []
            if vuelos_data and isinstance(vuelos_data, list):
                for v in vuelos_data:
                    if isinstance(v, dict):
                        loc_aero = (
                            v.get("codigo_reserva_aerolinea")
                            or v.get("airline_pnr")
                            or v.get("pnr_aerolinea")
                        )
                        if loc_aero:
                            break

        # Fallback para KIU: El localizador de la aerolínea es idéntico al localizador de reserva del sistema
        if not loc_aero and source_system.replace("AI_", "") == "KIU":
            loc_aero = data.get("CODIGO_RESERVA") or data.get("pnr") or data.get("localizador_pnr")

        from apps.common.utils.images import get_agencia_logo_b64

        # Colores de la agencia
        color_primario = (
            getattr(agencia_obj, "color_primario", None)
            or getattr(agencia_obj, "primary_color", None)
            or "#0052cc"
        )
        is_dark = PdfGenerationService._is_dark_color(color_primario)

        agencia_nombre = (
            agencia_obj.nombre
            if agencia_obj
            else data.get("AGENTE_EMISOR", "GRUPO SOPORTE GLOBAL INC")
        )
        agencia_nombre_comercial = agencia_obj.nombre_comercial if agencia_obj else agencia_nombre

        class SafeAgencia:
            """SafeAgencia."""

            def __init__(self, obj, color):
                self._obj = obj
                self.color_primario = color

            def __getattr__(self, name):
                if self._obj and hasattr(self._obj, name):
                    val = getattr(self._obj, name)
                    if val is not None:
                        return val
                defaults = {
                    "nombre": "TRAVELHUB",
                    "nombre_comercial": "TRAVELHUB",
                    "color_kiu": "#10b981",
                    "color_sabre": "#E50914",
                    "color_amadeus": "#0C66E1",
                    "eslogan": "",
                    "pie_pagina": "",
                    "instagram": "",
                    "email_principal": "info@travelhub.com",
                    "telefono_principal": "+58 412 331 2314",
                    "direccion": "Venezuela",
                    "iata": "",
                    "pk": None,
                    "id": None,
                }
                return defaults.get(name, "")

        safe_agencia = SafeAgencia(agencia_obj, color_primario)

        # Documento / FOID del pasajero
        foid_doc = (
            data.get("CODIGO_IDENTIFICACION")
            or data.get("FOID")
            or data.get("foid")
            or data.get("foid_pasajero")
            or data.get("passenger_document")
            or data.get("documento_pasajero")
            or (boleto_obj.foid_pasajero if boleto_obj else None)
        )
        if (
            not foid_doc
            and boleto_obj
            and getattr(boleto_obj, "venta_asociada", None)
            and getattr(boleto_obj.venta_asociada, "cliente", None)
        ):
            cliente_obj = boleto_obj.venta_asociada.cliente
            foid_doc = (
                cliente_obj.cedula_identidad
                or cliente_obj.numero_pasaporte
                or getattr(cliente_obj, "numero_documento", None)
            )

        return {
            "agencia": safe_agencia,
            "agencia_logo_b64": get_agencia_logo_b64(agencia_obj, is_dark_bg=is_dark)
            if agencia_obj
            else None,
            "agencia_nombre": agencia_nombre,
            "agencia_nombre_comercial": agencia_nombre_comercial,
            "is_dark_color": is_dark,
            "NOMBRE_DEL_PASAJERO": nombre_original,
            "CODIGO_IDENTIFICACION": foid_doc or "---",
            "NUMERO_DE_BOLETO": data.get("NUMERO_DE_BOLETO")
            or data.get("ticket_number")
            or data.get("numero_boleto")
            or (boleto_obj.numero_boleto if boleto_obj else None),
            "FECHA_DE_EMISION": f_emision,
            "CODIGO_RESERVA": data.get("CODIGO_RESERVA")
            or data.get("pnr")
            or data.get("localizador_pnr"),
            "CODIGO_RESERVA_AEROLINEA": loc_aero,
            "NOMBRE_AEROLINEA": data.get("NOMBRE_AEROLINEA")
            or data.get("nombre_aerolinea")
            or data.get("aerolinea_emisora")
            or data.get("issuing_airline")
            or data.get("airline")
            or "AEROLINEA",
            "SOURCE_SYSTEM": source_system.replace("AI_", ""),
            "TARIFA_BASE": data.get("TARIFA_IMPORTE")
            or data.get("fare_amount")
            or data.get("tarifa_base")
            or "0.00",
            "TOTAL": data.get("TOTAL")
            or data.get("total_amount")
            or data.get("total_boleto")
            or "0.00",
            "TOTAL_MONEDA": data.get("TOTAL_MONEDA")
            or data.get("moneda")
            or data.get("total_currency")
            or "USD",
            "AGENTE_EMISOR": agente or "10617390",
            "vuelos": data.get("segmentos")
            or data.get("vuelos")
            or data.get("itinerario")
            or data.get("flights")
            or [],
            "solo_nombre_pasajero": solo_nombre,
            "es_remision": data.get("es_remision", False),
        }

    @staticmethod
    def generate_ticket_pdf(data: dict[str, Any], agencia_obj=None, **kwargs) -> tuple[bytes, str]:
        return PdfGenerationService.generate_ticket(data, agencia_obj, **kwargs)

    @staticmethod
    def _is_dark_color(hex_color: str) -> bool:
        try:
            hex_color = str(hex_color).lstrip("#")
            if len(hex_color) == 3:
                hex_color = "".join([c * 2 for c in hex_color])
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
            return yiq < 128
        except Exception as e:
            logger.warning(f"No se pudo calcular luminosidad del color '{hex_color}': {e}")
            return True


def generate_ticket_pdf(data: dict[str, Any], agencia_obj=None, **kwargs) -> tuple[bytes, str]:
    """generate_ticket_pdf."""
    return PdfGenerationService.generate_ticket(data, agencia_obj, **kwargs)

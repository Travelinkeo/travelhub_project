import logging
import re
from datetime import datetime

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse

from apps.bookings.models import SegmentoVuelo
from apps.common.models import Ciudad
from apps.common.services.catalog_service import CatalogNormalizationService

logger = logging.getLogger(__name__)


def _parse_date_robust(date_str):
    """
    Intenta parsear fechas en formatos comunes de GDS (25APR, 25 APR 2024, etc)
    """
    if not date_str or str(date_str).strip() == "":
        return None

    date_str = str(date_str).upper().strip()
    # Limpieza de ruidos comunes
    date_str = re.sub(r"^(?:EMISION|ISSUED|DATE|FECHA)[:\s]+", "", date_str)

    # Diccionario de meses en español
    meses_es = {
        "ENE": "JAN",
        "FEB": "FEB",
        "MAR": "MAR",
        "ABR": "APR",
        "MAY": "MAY",
        "JUN": "JUN",
        "JUL": "JUL",
        "AGO": "AUG",
        "SEP": "SEP",
        "OCT": "OCT",
        "NOV": "NOV",
        "DIC": "DEC",
    }
    for es, en in meses_es.items():
        if es in date_str:
            date_str = date_str.replace(es, en)

    formatos = ["%d%b", "%d %b", "%d %b %Y", "%d%b%y", "%d%b%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

    # Intentar con meses en inglés (estándar GDS)
    for fmt in formatos:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year == 1900:
                now = datetime.now()
                dt = dt.replace(year=now.year)
            return dt.date()
        except (ValueError, TypeError):
            continue

    return None


class ItineraryCryptoService:
    """
    Servicio de generación y descifrado de tokens efímeros firmados criptográficamente
    para acceso seguro a itinerarios de pasajeros sin requerimiento de login.
    """

    # Salt único para aislar criptográficamente el alcance de este token
    SALT = "travelhub.itinerary.v1"

    @classmethod
    def generar_enlace_itinerario(cls, venta) -> str:
        """
        Empaqueta la tupla (id_venta, agencia_id) en un token seguro con marca de tiempo
        y construye la URL absoluta para el cliente.
        """
        signer = TimestampSigner(salt=cls.SALT)
        # Serializamos los datos críticos en una cadena simple
        payload = f"{venta.pk}:{venta.agencia_id}"
        token = signer.sign(payload)

        # Construimos la ruta relativa
        path = reverse("bookings:public_itinerary_live", kwargs={"token": token})

        # Retornamos la URL absoluta del inquilino si está definida (SaaS Ready), de lo contrario relativa
        domain = getattr(settings, "SITE_DOMAIN", "")
        if domain:
            if not (domain.startswith("http://") or domain.startswith("https://")):
                domain = f"https://{domain}"
            return f"{domain}{path}"
        return path

    @classmethod
    def verificar_y_desempaquetar_token(cls, token: str, max_age_days: int = 30) -> tuple:
        """
        Valida la firma criptográfica y la vigencia del token.
        Retorna una tupla (venta_id, agencia_id) o levanta excepciones de seguridad.
        """
        signer = TimestampSigner(salt=cls.SALT)

        # Convertimos los días de vigencia a segundos (Defensa por expiración)
        max_age_seconds = max_age_days * 24 * 60 * 60

        try:
            # Desfirmamos validando la marca de tiempo del servidor
            payload = signer.unsign(token, max_age=max_age_seconds)
            venta_id, agencia_id = payload.split(":")
            return int(venta_id), int(agencia_id)

        except (SignatureExpired, BadSignature) as e:
            # Propagamos el fallo controlado para manejo en la capa de control (View)
            raise e


class ItineraryService:
    @staticmethod
    def sync_segments(data, agencia, venta, item_venta_obj, aerolinea_default):
        """
        Synchronizes flight segments for a sale.
        """
        itinerario = data.get("segmentos") or data.get("itinerario") or data.get("flights", [])

        for seg in itinerario:
            try:
                # Resolve Cities
                iata_dep = seg.get("codigo_iata_origen")
                iata_arr = seg.get("codigo_iata_destino")

                ciudad_dep = None
                ciudad_arr = None

                if iata_dep:
                    ciudad_dep = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_dep)
                if iata_arr:
                    ciudad_arr = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_arr)

                if not ciudad_dep:
                    dep_loc = seg.get("origen") or seg.get("departure", {}).get("location") or "N/A"
                    clean_name = str(dep_loc).split(",")[0].split("(")[0].strip()
                    ciudad_dep = Ciudad.objects.filter(nombre__iexact=clean_name).first()

                if not ciudad_arr:
                    arr_loc = seg.get("destino") or seg.get("arrival", {}).get("location") or "N/A"
                    clean_name = str(arr_loc).split(",")[0].split("(")[0].strip()
                    ciudad_arr = Ciudad.objects.filter(nombre__iexact=clean_name).first()

                # Sync Segment
                vuelo_num = str(
                    seg.get("vuelo") or seg.get("flightNumber") or seg.get("flight_number") or "N/A"
                )
                f_salida = _parse_date_robust(str(seg.get("fecha_salida") or seg.get("date")))

                seg_existente = SegmentoVuelo.objects.filter(
                    venta=venta, numero_vuelo=vuelo_num, fecha_salida=f_salida
                ).first()

                seg_data = {
                    "agencia": agencia,
                    "venta": venta,
                    "item_venta": item_venta_obj,
                    "origen": ciudad_dep,
                    "destino": ciudad_arr,
                    "aerolinea": seg.get("airline") or seg.get("aerolinea") or aerolinea_default,
                    "numero_vuelo": vuelo_num,
                    "clase_reserva": str(
                        seg.get("details", {}).get("cabin") or seg.get("clase") or "Y"
                    )[:5],
                    "fecha_salida": f_salida,
                    "fecha_llegada": _parse_date_robust(str(seg.get("fecha_llegada"))),
                }

                if seg_existente:
                    for key, value in seg_data.items():
                        setattr(seg_existente, key, value)
                    seg_existente.save()
                    logger.info(f"✈️ SegmentoVuelo actualizado: {vuelo_num}")
                else:
                    SegmentoVuelo.objects.create(**seg_data)
                    logger.info(f"✈️ SegmentoVuelo creado: {vuelo_num}")

            except Exception as seg_err:
                logger.error(f"Error procesando segmento de vuelo: {seg_err}")

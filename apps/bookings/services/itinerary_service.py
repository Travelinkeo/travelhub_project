import logging
import re
from datetime import datetime

from django.conf import settings
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse

from apps.bookings.models import SegmentoVuelo
from apps.common.models import Ciudad
from apps.common.services.catalog_service import CatalogNormalizationService

logger = logging.getLogger(__name__)


def _parse_datetime_robust(date_str, time_str=None):
    """
    Intenta parsear fechas y horas en formatos comunes de GDS (25APR, 25 APR 2024, 18:30, etc)
    Retorna un objeto datetime.datetime con la hora correcta si está disponible.
    """
    if not date_str or str(date_str).strip() in ("", "None", "null", "N/A"):
        return None

    date_str = str(date_str).upper().strip()
    # Limpieza de ruidos comunes
    date_str = re.sub(r"^(?:EMISION|ISSUED|DATE|FECHA)[:\s]+", "", date_str)

    from core.models.ai_schemas import MESES_ES_TO_EN

    for es, en in MESES_ES_TO_EN.items():
        if es in date_str:
            date_str = date_str.replace(es, en)

    # Limpiar time_str
    clean_time = None
    if time_str and str(time_str).strip() not in ("", "None", "null", "N/A", "--:--"):
        t_raw = str(time_str).strip().replace(".", ":").replace(" ", "")
        if len(t_raw) == 4 and t_raw.isdigit():
            t_raw = f"{t_raw[:2]}:{t_raw[2:]}"
        m_time = re.search(r"(\d{1,2}):(\d{2})", t_raw)
        if m_time:
            clean_time = (int(m_time.group(1)), int(m_time.group(2)))

    # Formatos combinados (si date_str ya incluye hora)
    formatos_dt = [
        "%d%b%y %H:%M",
        "%d%b%Y %H:%M",
        "%d %b %Y %H:%M",
        "%d %b %y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M",
    ]

    from django.utils import timezone

    tz = timezone.get_current_timezone()

    for fmt in formatos_dt:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, tz)
            return dt
        except (ValueError, TypeError):
            continue

    # Formatos solo fecha
    formatos_d = [
        "%d%b%y",
        "%d%b%Y",
        "%d %b %Y",
        "%d %b %y",
        "%d%b",
        "%d %b",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    for fmt in formatos_d:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            if clean_time:
                dt = dt.replace(hour=clean_time[0], minute=clean_time[1])
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, tz)
            return dt
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
    def generar_enlace_itinerario(cls, venta, request=None) -> str:
        """
        Empaqueta la tupla (id_venta, agencia_id) en un token seguro con marca de tiempo
        y construye la URL absoluta para el cliente usando signing.dumps (URL-Safe).
        """
        token = signing.dumps({"v": venta.pk, "a": venta.agencia_id}, salt=cls.SALT, compress=True)

        # Construimos la ruta relativa limpia en la raíz
        path = reverse("public_itinerary_root", kwargs={"token": token})

        # 1. Si tenemos el objeto request, usamos el host real de la petición
        if request is not None:
            try:
                scheme = "https" if request.is_secure() else "http"
                host = request.get_host()
                if host:
                    return f"{scheme}://{host}{path}"
            except Exception as e:
                logger.debug("Host no disponible en request: %s", e)

        # 2. Si la agencia tiene un dominio o subdominio configurado
        agencia = getattr(venta, "agencia", None)
        if agencia:
            dominio_custom = getattr(agencia, "dominio_personalizado", None)
            if dominio_custom and str(dominio_custom).strip():
                domain = str(dominio_custom).strip()
                if not (domain.startswith("http://") or domain.startswith("https://")):
                    domain = f"https://{domain}"
                return f"{domain}{path}"

            subdominio = getattr(agencia, "subdominio", None)
            if subdominio and str(subdominio).strip():
                main = getattr(settings, "MAIN_DOMAIN", "travelhub.cc")
                return f"https://{subdominio.strip()}.{main}{path}"

        # 3. Fallback a dominio principal del sistema
        domain = (
            getattr(settings, "SITE_DOMAIN", "")
            or getattr(settings, "MAIN_DOMAIN", "")
            or getattr(settings, "EMAIL_DOMAIN", "")
            or "travelhub.cc"
        ).strip()

        if domain:
            if not (domain.startswith("http://") or domain.startswith("https://")):
                domain = f"https://{domain}"
            return f"{domain}{path}"

        return f"https://travelhub.cc{path}"

    @classmethod
    def verificar_y_desempaquetar_token(cls, token: str, max_age_days: int = 30) -> tuple:
        """
        Valida la firma criptográfica y la vigencia del token.
        Retorna una tupla (venta_id, agencia_id) o levanta excepciones de seguridad.
        """
        # Convertimos los días de vigencia a segundos (Defensa por expiración)
        max_age_seconds = max_age_days * 24 * 60 * 60

        try:
            data = signing.loads(token, salt=cls.SALT, max_age=max_age_seconds)
            if isinstance(data, dict):
                return int(data["v"]), int(data["a"]) if data.get("a") is not None else None
            elif isinstance(data, list | tuple):
                return int(data[0]), int(data[1]) if len(data) > 1 and data[1] is not None else None
        except Exception as err:
            logger.debug("Fallo parsing signing.loads, intentando TimestampSigner: %s", err)

        # Fallback de compatibilidad con TimestampSigner legado (formato id:agencia:timestamp:signature)
        try:
            signer = TimestampSigner(salt=cls.SALT)
            payload = signer.unsign(token, max_age=max_age_seconds)
            parts = payload.split(":")
            venta_id = int(parts[0])
            agencia_id = int(parts[1]) if len(parts) > 1 and parts[1] != "None" else None
            return venta_id, agencia_id
        except (SignatureExpired, BadSignature) as e:
            raise e from None
        except Exception as e:
            raise BadSignature(f"Token inválido: {e}") from None


class ItineraryService:
    """ItineraryService."""

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
                hora_dep = (
                    seg.get("hora_salida")
                    or seg.get("departure", {}).get("time")
                    or seg.get("departure_time")
                )
                hora_arr = (
                    seg.get("hora_llegada")
                    or seg.get("arrival", {}).get("time")
                    or seg.get("arrival_time")
                )

                f_salida = _parse_datetime_robust(
                    seg.get("fecha_salida") or seg.get("date"), hora_dep
                )
                f_llegada = _parse_datetime_robust(
                    seg.get("fecha_llegada") or seg.get("fecha_salida") or seg.get("date"),
                    hora_arr,
                )

                seg_existente = SegmentoVuelo.objects.filter(
                    venta=venta, numero_vuelo=vuelo_num
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
                    "fecha_llegada": f_llegada,
                }

                if seg_existente:
                    for key, value in seg_data.items():
                        setattr(seg_existente, key, value)
                    seg_existente.save()
                    logger.info(f" SegmentoVuelo actualizado: {vuelo_num}")
                else:
                    SegmentoVuelo.objects.create(**seg_data)
                    logger.info(f" SegmentoVuelo creado: {vuelo_num}")

            except Exception as seg_err:
                logger.error(f"Error procesando segmento de vuelo: {seg_err}")

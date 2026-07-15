import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.cache import cache

from apps.finance.models_stubs import TasaCambio
from core.tasks import send_telegram_task

logger = logging.getLogger(__name__)


def obtener_tasa_bcv_resiliente(moneda: str = "USD") -> Decimal:
    """
    Motor de obtención de tasas con Fallback y Caché de Supervivencia.
    Utiliza pyDolarVenezuela para evadir bloqueos del gobierno.
    Retorna Decimal para evitar errores de precisión en cálculos financieros.
    """
    hoy = date.today()
    moneda_iso = moneda.upper()

    # 1. INTENTO PRIMARIO: Consultar al BCV en vivo
    try:
        from pyDolarVenezuela import Monitor
        from pyDolarVenezuela.pages import BCV

        monitor = Monitor(BCV)

        monitores = monitor.get_all_monitors()

        target_key = moneda_iso.lower()

        monitor_data = None
        for m in monitores:
            m_key = m.get("key") if isinstance(m, dict) else getattr(m, "key", None)
            if m_key == target_key:
                monitor_data = m
                break

        if monitor_data:
            raw_price = (
                monitor_data.get("price", 0)
                if isinstance(monitor_data, dict)
                else getattr(monitor_data, "price", 0)
            )
            tasa_decimal = _to_decimal(raw_price)

            if tasa_decimal > 0:
                TasaCambio.objects.update_or_create(
                    fecha=hoy, moneda=moneda_iso, defaults={"monto": tasa_decimal}
                )
                cache.delete("tasa_bcv_context")

                logger.info(f"Tasa BCV obtenida en vivo: {tasa_decimal} {moneda_iso}")
                return tasa_decimal

        raise ValueError(f"Monitor {moneda_iso} no encontrado en la respuesta del BCV")

    except Exception as e:
        logger.warning(f"Fallo al contactar al BCV (posible caida del servidor): {str(e)}")

    # 1.5 INTENTO ADICIONAL: Fallback a DolarApi via bcv_scraper
    try:
        from apps.finance.services.bcv_scraper import obtener_tasas_bcv

        tasas_bcv = obtener_tasas_bcv()
        if tasas_bcv and moneda_iso in tasas_bcv:
            tasa_decimal = _to_decimal(tasas_bcv[moneda_iso])
            if tasa_decimal > 0:
                TasaCambio.objects.update_or_create(
                    fecha=hoy, moneda=moneda_iso, defaults={"monto": tasa_decimal}
                )
                cache.delete("tasa_bcv_context")
                logger.info(f"Tasa BCV obtenida via DolarApi: {tasa_decimal} {moneda_iso}")
                return tasa_decimal
    except Exception as api_err:
        logger.warning(f"Fallo en DolarApi fallback para resiliente: {api_err}")

    # 2. INTENTO SECUNDARIO (FALLBACK): Activar Cache de Supervivencia
    try:
        ultima_tasa = TasaCambio.objects.filter(moneda=moneda_iso).latest("fecha")

        logger.error(
            f"BCV CAIDO. Usando Cache de Supervivencia: {ultima_tasa.monto} del {ultima_tasa.fecha}"
        )

        mensaje_alerta = (
            f"ALERTA FINANCIERA - TRAVELHUB\n\n"
            f"El portal del BCV no responde o cambio su estructura anti-bots.\n"
            f"Cache de Supervivencia Activado.\n"
            f"Facturacion temporal con la tasa mas reciente: {ultima_tasa.monto} Bs ({ultima_tasa.fecha}).\n"
            f"Tus ventas no se han detenido."
        )
        send_telegram_task.delay(mensaje_alerta)

        return ultima_tasa.monto

    except TasaCambio.DoesNotExist:
        logger.critical("BCV CAIDO Y CACHE DE SUPERVIVENCIA VACIO. ALTA GRAVEDAD.")
        return Decimal("0")


def _to_decimal(value) -> Decimal:
    """Convierte un valor a Decimal de forma segura, evitando errores de punto flotante."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")

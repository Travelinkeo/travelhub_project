import logging
import secrets

from django.core.cache import cache

logger = logging.getLogger(__name__)


def agency_context(request):
    agencia = None
    rol = None
    user_agencies = []  # Lista de agencias del usuario para el selector

    if request.user.is_authenticated:
        agencia = getattr(request, "agencia", None)

        from core.models.agencia import UsuarioAgencia

        # Obtener todas las agencias activas del usuario
        vinculos = (
            UsuarioAgencia.objects.filter(usuario=request.user, activo=True, agencia__activa=True)
            .select_related("agencia")
            .order_by("agencia__nombre")
        )
        user_agencies = list(vinculos)

        vinculo = next((v for v in user_agencies if agencia and v.agencia_id == agencia.id), None)
        if vinculo:
            rol = vinculo.rol
        elif request.user.is_superuser:
            rol = "admin"

    try:
        from datetime import date

        from apps.finance.models_stubs import TasaCambio

        tasa_usd_obj = TasaCambio.objects.filter(moneda="USD").order_by("-fecha").first()
        tasa_eur_obj = TasaCambio.objects.filter(moneda="EUR").order_by("-fecha").first()
        tasa_p2p_obj = TasaCambio.objects.filter(moneda="P2P").order_by("-fecha").first()

        es_obsoleta = False
        hoy = date.today()
        if not tasa_usd_obj or tasa_usd_obj.fecha < hoy:
            es_obsoleta = True
        elif not tasa_eur_obj or tasa_eur_obj.fecha < hoy:
            es_obsoleta = True
        elif not tasa_p2p_obj or tasa_p2p_obj.fecha < hoy:
            es_obsoleta = True

        if es_obsoleta and not cache.get("bcv_sync_lock"):
            cache.set("bcv_sync_lock", True, timeout=1800)

            try:
                from apps.contabilidad.tasks import sync_bcv_rates

                sync_bcv_rates.delay()
            except Exception as e:
                logger.debug("Ignored exception syncing BCV rates: %s", e)

        tasas = cache.get("tasa_bcv_context")
        if tasas is None:
            tasas = {
                "usd": f"{tasa_usd_obj.monto:,.2f}" if tasa_usd_obj else "N/D",
                "eur": f"{tasa_eur_obj.monto:,.2f}" if tasa_eur_obj else "N/D",
                "p2p": f"{tasa_p2p_obj.monto:,.2f}" if tasa_p2p_obj else "N/D",
            }
            cache.set("tasa_bcv_context", tasas, timeout=300)
        tasa_usd = tasas["usd"]
        tasa_eur = tasas["eur"]
        tasa_p2p = tasas["p2p"]
    except Exception:
        tasa_usd = "N/D"
        tasa_eur = "N/D"
        tasa_p2p = "N/D"

    session = getattr(request, "session", {})
    return {
        "current_agency": agencia,
        "user_agency_role": rol,
        "user_agencies": user_agencies,  # Lista de UsuarioAgencia para el switcher
        "is_superuser": request.user.is_authenticated and request.user.is_superuser,
        "tasa_usd": tasa_usd,
        "tasa_eur": tasa_eur,
        "tasa_p2p": tasa_p2p,
        "is_impersonating": "impersonated_agencia_id" in session,
        "impersonated_agencia_name": session.get("impersonated_agencia_name")
        if hasattr(session, "get")
        else None,
        # Live chat — activa el widget si LIVE_CHAT_ID está en .env
        "LIVE_CHAT_ID": getattr(
            __import__("django.conf", fromlist=["settings"]).settings, "LIVE_CHAT_ID", ""
        ),
    }


def csp_nonce(request):
    """Retorna el nonce generado por el middleware para su uso en plantillas."""
    nonce = getattr(request, "csp_nonce", "")
    if not nonce:
        # Fallback de seguridad si el middleware no se ejecutó
        nonce = secrets.token_hex(16)
        request.csp_nonce = nonce
    return {
        "csp_nonce": nonce,
        "CSP_NONCE": nonce,  # Compatibilidad con plantillas legacy
    }

import secrets

from django.core.cache import cache


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
        import threading
        from datetime import date

        from apps.finance.models.currencies import TasaCambio

        tasa_usd_obj = TasaCambio.objects.filter(moneda="USD").order_by("-fecha").first()
        tasa_eur_obj = TasaCambio.objects.filter(moneda="EUR").order_by("-fecha").first()

        # 🛡️ Sincronización pasiva en segundo plano
        # Si la base de datos está vacía, o si la tasa más reciente es de un día anterior,
        # y no hay un hilo de sincronización ejecutándose/bloqueado recientemente.
        es_obsoleta = False
        hoy = date.today()
        if not tasa_usd_obj or tasa_usd_obj.fecha < hoy:
            es_obsoleta = True
        elif not tasa_eur_obj or tasa_eur_obj.fecha < hoy:
            es_obsoleta = True

        if es_obsoleta and not cache.get("bcv_sync_lock"):
            # Establecer un bloqueo temporal de 30 minutos para evitar hilos concurrentes
            cache.set("bcv_sync_lock", True, timeout=1800)

            # Lanzar actualización en segundo plano
            def async_sync():
                try:
                    from apps.contabilidad.tasas_venezuela_client import TasasVenezuelaClient

                    TasasVenezuelaClient.actualizar_tasas_db()
                except Exception as sync_err:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Error en hilo de sincronización pasiva de tasas BCV: {sync_err}")

            threading.Thread(target=async_sync, daemon=True).start()

        tasas = cache.get("tasa_bcv_context")
        if tasas is None:
            tasas = {
                "usd": f"{tasa_usd_obj.monto:,.2f}" if tasa_usd_obj else "474.05",
                "eur": f"{tasa_eur_obj.monto:,.2f}" if tasa_eur_obj else "550.89",
            }
            cache.set("tasa_bcv_context", tasas, timeout=300)
        tasa_usd = tasas["usd"]
        tasa_eur = tasas["eur"]
    except Exception:
        tasa_usd = "474.05"
        tasa_eur = "550.89"

    session = getattr(request, "session", {})
    return {
        "current_agency": agencia,
        "user_agency_role": rol,
        "user_agencies": user_agencies,  # Lista de UsuarioAgencia para el switcher
        "is_superuser": request.user.is_authenticated and request.user.is_superuser,
        "tasa_usd": tasa_usd,
        "tasa_eur": tasa_eur,
        "is_impersonating": "impersonated_agencia_id" in session,
        "impersonated_agencia_name": session.get("impersonated_agencia_name")
        if hasattr(session, "get")
        else None,
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

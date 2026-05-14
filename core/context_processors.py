import secrets

from django.core.cache import cache


def agency_context(request):
    agencia = None
    rol = None

    if request.user.is_authenticated:
        agencia = getattr(request, 'agencia', None)

        from core.models.agencia import UsuarioAgencia
        vinculo = UsuarioAgencia.objects.filter(usuario=request.user, agencia=agencia, activo=True).first()
        if vinculo:
            rol = vinculo.rol
        elif request.user.is_superuser:
            rol = 'admin'

    try:
        tasas = cache.get('tasa_bcv_context')
        if tasas is None:
            from apps.finance.models.currencies import TasaCambio
            tasa_usd_obj = TasaCambio.objects.filter(moneda='USD').order_by('-fecha').first()
            tasa_eur_obj = TasaCambio.objects.filter(moneda='EUR').order_by('-fecha').first()
            tasas = {
                'usd': f"{tasa_usd_obj.monto:,.2f}" if tasa_usd_obj else "474.05",
                'eur': f"{tasa_eur_obj.monto:,.2f}" if tasa_eur_obj else "550.89",
            }
            cache.set('tasa_bcv_context', tasas, timeout=300)
        tasa_usd = tasas['usd']
        tasa_eur = tasas['eur']
    except Exception:
        tasa_usd = "474.05"
        tasa_eur = "550.89"

    session = getattr(request, 'session', {})
    return {
        'current_agency': agencia,
        'user_agency_role': rol,
        'is_superuser': request.user.is_authenticated and request.user.is_superuser,
        'tasa_usd': tasa_usd,
        'tasa_eur': tasa_eur,
        'is_impersonating': 'impersonated_agencia_id' in session,
        'impersonated_agencia_name': session.get('impersonated_agencia_name') if hasattr(session, 'get') else None,
    }

def csp_nonce(request):
    """Retorna el nonce generado por el middleware para su uso en plantillas."""
    nonce = getattr(request, 'csp_nonce', '')
    if not nonce:
        # Fallback de seguridad si el middleware no se ejecutó
        nonce = secrets.token_hex(16)
        request.csp_nonce = nonce
        
    return {
        'csp_nonce': nonce,
        'CSP_NONCE': nonce  # Compatibilidad con plantillas legacy
    }
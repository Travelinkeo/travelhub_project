import secrets

def agency_context(request):
    agencia = None
    rol = None
    
    # 1. Recuperar la Agencia y el Rol del usuario logueado
    if request.user.is_authenticated:
        ua = getattr(request.user, 'agencias', None)
        if ua:
            vinculo = ua.filter(activo=True).first()
            if vinculo:
                agencia = vinculo.agencia
                rol = vinculo.rol
            
    # 2. Recuperar la tasa BCV más reciente
    try:
        from core.models_catalogos import TasaCambio
        tasa_usd_obj = TasaCambio.objects.filter(moneda='USD').order_by('-fecha').first()
        tasa_eur_obj = TasaCambio.objects.filter(moneda='EUR').order_by('-fecha').first()
        
        tasa_usd = f"{tasa_usd_obj.monto:,.2f}" if tasa_usd_obj else "474.05"
        tasa_eur = f"{tasa_eur_obj.monto:,.2f}" if tasa_eur_obj else "550.89"
    except Exception:
        tasa_usd = "474.05"
        tasa_eur = "550.89"

    return {
        'current_agency': agencia,
        'user_agency_role': rol,
        # 🔥 BLINDAJE: Si la BD está vacía, mostramos la última tasa conocida de hoy (2 de abril)
        'tasa_usd': tasa_usd,
        'tasa_eur': tasa_eur,
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
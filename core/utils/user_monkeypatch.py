import logging

logger = logging.getLogger(__name__)

def get_user_agency(user):
    """
    Inyecta la propiedad 'agencia' al modelo User.
    Retorna la agencia activa asociada al usuario.
    """
    if not user.is_authenticated:
        return None

    # Intentar obtener del ThreadLocal (Middleware) para mayor eficiencia
    from core.middleware import get_current_agency
    agency = get_current_agency()
    if agency:
        return agency

    # Si no hay request (shell, cron, background), buscar en la base de datos
    try:
        from core.models.agencia import UsuarioAgencia
        # UsuarioAgencia no usa TenantManager, por lo que no hay recursión aquí
        ua = UsuarioAgencia.objects.filter(usuario=user, activo=True).select_related('agencia').first()
        if ua:
            return ua.agencia
    except Exception as e:
        logger.debug(f"Error recuperando agencia para usuario {user.id}: {e}")
        pass
    
    return None

def get_user_role(user):
    """
    Inyecta la propiedad 'rol_agencia' al modelo User.
    """
    if not user.is_authenticated:
        return None

    try:
        from core.models.agencia import UsuarioAgencia
        ua = UsuarioAgencia.objects.filter(usuario=user, activo=True).first()
        if ua:
            return ua.rol
    except Exception:
        pass
    
    return 'vendedor'  # Rol por defecto

def agency_context(request):
    """
    Context processor to add the current user's agency to the template context.
    """
    if request.user.is_authenticated and hasattr(request.user, 'agencias'):
        ua = request.user.agencias.filter(activo=True).first()
        if ua:
            return {
                'current_agency': ua.agencia,
                'user_agency_role': ua.rol
            }
    return {}

def csp_nonce(request):
    return {'csp_nonce': request.META.get('CSP_NONCE')}

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

from core.security import get_user_active_agency


class SaaSMixin:
    """
    Mixin para filtrar querysets por la agencia del usuario actual.
    Asume que el modelo tiene un campo 'agencia'.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return qs.none()
            
        if user.is_superuser:
            return qs
            
        # Obtener la agencia activa del usuario (optimizado con select_related)
        agencia = get_user_active_agency(user)
        if agencia:
            # Solo filtrar por agencia si el modelo tiene ese campo
            if hasattr(qs.model, 'agencia'):
                return qs.filter(agencia=agencia)
            return qs
        
        # Si no tiene agencia asignada, no ve nada (o manejar según lógica de negocio)
        return qs.none()

    def form_valid(self, form):
        """
        Asigna automáticamente la agencia al crear un objeto.
        """
        user = self.request.user
        if not user.is_superuser and hasattr(form.instance, 'agencia'):
            agencia = get_user_active_agency(user)
            if agencia:
                form.instance.agencia = agencia
        return super().form_valid(form)


class AgencyRoleRequiredMixin(AccessMixin, SaaSMixin):
    """
    Mixin para restringir vistas a roles específicos dentro de la agencia.
    Uso: 
    allowed_roles = ['admin', 'gerente']
    """
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
            
        agencia = get_user_active_agency(request.user)
        if hasattr(request.user, 'agencias'):
            usuario_agencia = request.user.agencias.filter(activo=True).first()
            if usuario_agencia and usuario_agencia.rol in self.allowed_roles:
                return super().dispatch(request, *args, **kwargs)
        
        raise PermissionDenied("No tienes permisos suficientes para realizar esta acción.")


class HtmxResponseMixin:
    """Devuelve un template parcial si la petición viene de HTMX"""
    htmx_template_name = None

    def get_template_names(self):
        if self.request.headers.get('HX-Request') and self.htmx_template_name:
            return [self.htmx_template_name]
        return super().get_template_names()

from django.db import models
from django.utils import timezone
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from core.models.base import SoftDeleteModel, AgenciaManager as SoftDeleteManager


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
            
        # Obtener la agencia activa del usuario
        # Asumimos que el usuario tiene una relación inversa 'agencias' (UsuarioAgencia)
        if hasattr(user, 'agencias'):
            usuario_agencia = user.agencias.filter(activo=True).first()
            if usuario_agencia:
                return qs.filter(agencia=usuario_agencia.agencia)
        
        # Si no tiene agencia asignada, no ve nada (o manejar según lógica de negocio)
        return qs.none()

    def form_valid(self, form):
        """
        Asigna automáticamente la agencia al crear un objeto.
        """
        user = self.request.user
        if not user.is_superuser and hasattr(form.instance, 'agencia'):
            if hasattr(user, 'agencias'):
                usuario_agencia = user.agencias.filter(activo=True).first()
                if usuario_agencia:
                    form.instance.agencia = usuario_agencia.agencia
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

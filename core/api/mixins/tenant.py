from rest_framework import permissions
from django.core.exceptions import PermissionDenied

class TenantViewSetMixin:
    """
    Mixin para ViewSets de DRF que asegura el aislamiento multi-tenant.
    Sobrescribe get_queryset para filtrar siempre por la agencia del usuario autenticado.
    """
    def get_queryset(self):
        user = self.request.user
        
        # Superusuarios pueden ver todo (God Mode)
        if user.is_superuser:
            return super().get_queryset()
            
        # Obtener la agencia activa del usuario desde la relación inversa
        if hasattr(user, 'agencias'):
            usuario_agencia = user.agencias.filter(activo=True).first()
            if usuario_agencia:
                # El manager del modelo (AgenciaManager) ya debería filtrar,
                # pero aquí lo hacemos explícito para mayor seguridad.
                return super().get_queryset().filter(agencia=usuario_agencia.agencia)
        
        # Si no hay agencia activa, devolvemos un queryset vacío por seguridad.
        return super().get_queryset().none()

    def perform_create(self, serializer):
        """
        Asegura que al crear un objeto, se asigne la agencia del usuario.
        """
        user = self.request.user
        if not user.is_superuser:
            if hasattr(user, 'agencias'):
                usuario_agencia = user.agencias.filter(activo=True).first()
                if usuario_agencia:
                    serializer.save(agencia=usuario_agencia.agencia)
                    return
            raise PermissionDenied("No tienes una agencia activa asignada.")
        
        serializer.save()

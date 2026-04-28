from django.db import models
from django.core.exceptions import PermissionDenied
from core.middleware import get_current_agency, get_current_user

class AgenciaManager(models.Manager):
    """
    Manager que filtra automáticamente los resultados por la agencia del contexto actual.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        agency = get_current_agency()
        user = get_current_user()

        # Si hay una agencia en el contexto, filtramos por ella
        if agency:
            return queryset.filter(agencia=agency)
        
        # Si NO hay agencia en el contexto (ej: scripts de consola o tareas celery sin contexto)
        # pero el usuario es superuser, permitimos ver todo.
        if user and user.is_superuser:
            return queryset
            
        # Si no hay contexto y no es superuser, retornamos un queryset vacío por seguridad
        return queryset.none()

class AgenciaMixin(models.Model):
    """
    Mixin para modelos que requieren aislamiento multi-tenant.
    Añade el campo agencia y aplica el filtrado automático.
    """
    agencia = models.ForeignKey(
        'core.Agencia', 
        on_delete=models.CASCADE,
        related_name="%(class)s_items",
        null=True, 
        blank=True,
        db_index=True
    )

    # El manager por defecto filtra por agencia
    objects = AgenciaManager()
    
    # Manager sin filtros para casos especiales (admin, migraciones, etc)
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Asegura que la agencia se asigne automáticamente al guardar si no está presente.
        """
        if not self.agencia_id:
            current_agency = get_current_agency()
            if current_agency:
                self.agencia = current_agency
            elif not get_current_user() or not get_current_user().is_superuser:
                # Si no hay agencia en el contexto y no es superuser, prohibimos el guardado
                raise PermissionDenied("Se requiere una agencia para guardar este registro.")
        
        # Validación de cruce de datos (Seguridad extra)
        if self.agencia_id and get_current_agency() and self.agencia_id != get_current_agency().id:
            if not get_current_user().is_superuser:
                raise PermissionDenied("No puedes guardar datos en otra agencia.")
                
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Previene borrar datos de otra agencia."""
        if self.agencia_id and get_current_agency() and self.agencia_id != get_current_agency().id:
            if not get_current_user().is_superuser:
                raise PermissionDenied("No puedes borrar datos de otra agencia.")
        super().delete(*args, **kwargs)

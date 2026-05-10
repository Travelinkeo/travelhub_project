from django.db import models
import logging

logger = logging.getLogger(__name__)

class TenantManager(models.Manager):
    """
    Manager personalizado para asegurar el aislamiento de datos entre agencias (Multi-Tenancy).
    Filtra automáticamente el QuerySet por la agencia del contexto actual.
    """

    def get_queryset(self):
        """
        Sobrescribe el QuerySet base para inyectar filtros de Multi-Tenancy y Soft Delete.
        """
        from .middleware import get_current_agency


        
        queryset = super().get_queryset()

        # 1. 🛡️ FILTRADO SOFT DELETE: Ocultar registros borrados lógicamente
        # Si el modelo tiene el mixin de Soft Delete, filtramos por is_deleted=False.
        if hasattr(self.model, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)

        # 2. 🛡️ FILTRADO TENANT: Aislar datos por Agencia (Incluyendo Registros Globales)
        agency = get_current_agency()
        if agency:
            logger.debug(f"TenantManager: Filtrando por agencia {agency.id} + Globales")
            return queryset.filter(models.Q(agencia=agency) | models.Q(agencia__isnull=True))
        
        logger.warning(f"🛡️ SEGURIDAD: TenantManager en {self.model.__name__} sin contexto de agencia. Retornando QuerySet VACÍO.")
        return queryset.none()
        
        # ⚠️ IMPORTANTE: Lógica para tareas de fondo (Celery)
        # En Celery no hay un request activo, por lo que get_current_agency() devolverá None.
        # SOLUCIÓN: Utilizar el context manager 'agency_context' en la tarea:
        #
        # from core.middleware import agency_context
        # with agency_context(agencia):
        #     # Todas las consultas aquí estarán filtradas automáticamente
        #     Venta.objects.all()
        #
        # Si no se usa el context manager, se debe usar 'all_objects' para bypass manual.

class TenantModelMixin(models.Model):
    """
    Mixin para modelos que requieren Multi-Tenancy.
    Configura el TenantManager como default manager.
    """
    objects = TenantManager()
    all_objects = models.Manager() # Fallback para bypass de multi-tenancy (Admin/System)

    class Meta:
        abstract = True

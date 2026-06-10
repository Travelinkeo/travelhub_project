from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils import timezone

from core.middleware import get_current_agency, get_current_user


class SaasQuerySet(models.QuerySet):
    """
    QuerySet personalizado para forzar la inyección de la agencia en operaciones bulk.
    """

    def update(self, **kwargs):
        from core.middleware import get_current_agency, get_current_user, is_system_context

        user = get_current_user()
        if not is_system_context() and not (user and user.is_superuser):
            agency = get_current_agency()
            if agency:
                kwargs["agencia"] = agency
        return super().update(**kwargs)

    def bulk_create(self, objs, **kwargs):
        from core.middleware import get_current_agency, get_current_user, is_system_context

        user = get_current_user()
        if not is_system_context() and not (user and user.is_superuser):
            agency = get_current_agency()
            if agency:
                for obj in objs:
                    obj.agencia = agency
        return super().bulk_create(objs, **kwargs)


class AgenciaManager(models.Manager):
    """Manager Maestro: Filtra automáticamente por Agencia Y por estado de eliminación."""

    def get_queryset(self):
        from core.middleware import is_system_context

        if issubclass(self.model, SoftDeleteModel):
            queryset = SoftDeleteQuerySet(self.model, using=self._db)
        else:
            queryset = SaasQuerySet(self.model, using=self._db)

        # 1. FILTRO DE SOFT DELETE (Si el modelo lo soporta)
        if hasattr(self.model, "is_deleted"):
            queryset = queryset.filter(is_deleted=False)

        # 2. BYPASS DE SISTEMA (Celery, Tareas de Fondo, God Mode Explícito)
        if is_system_context():
            return queryset

        # 3. FILTRO DE MULTI-TENANCY
        agency = get_current_agency()
        user = get_current_user()

        # Caso A: Hay una agencia en el contexto (Contexto activo)
        if agency:
            # Retorna registros de la agencia + registros globales (sin agencia asignada)
            return queryset.filter(models.Q(agencia=agency) | models.Q(agencia__isnull=True))

        # Caso B: No hay agencia pero es un SUPERUSER (God Mode Global)
        if user and user.is_superuser:
            return queryset

        # Caso C: Comandos de gestión (Migrations, Shell, etc.)
        import sys

        if "pytest" in sys.modules or (
            "manage.py" in sys.argv
            and any(
                arg in sys.argv for arg in ["makemigrations", "migrate", "shell", "check", "test"]
            )
        ):
            return queryset

        # Caso D: Seguridad por defecto
        return queryset.none()


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet que permite operaciones bulk respetando soft-delete."""

    def delete(self):
        self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        super().delete()

    def restore(self):
        self.update(is_deleted=False, deleted_at=None)


class SoftDeleteManager(models.Manager):
    """Manager que retorna SoftDeleteQuerySet sin filtrar is_deleted."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    """
    Mixin para habilitar borrado lógico (Soft Delete).
    """

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    with_deleted = SoftDeleteManager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        """Sobrescribe el borrado físico por uno lógico."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, *args, **kwargs):
        """Borrado físico real de la base de datos.
        Salta la cadena MRO y llama directamente a models.Model.delete()
        para evitar que AgenciaMixin.delete() intercepte y aplique soft-delete."""
        models.Model.delete(self, *args, **kwargs)

    def restore(self):
        """Restaura un registro eliminado."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class AgenciaMixin(models.Model):
    """
    Mixin para modelos que requieren aislamiento multi-tenant.
    Añade el campo agencia y aplica el filtrado automático.
    """

    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        related_name="%(class)s_items",
        null=True,
        blank=True,
        db_index=True,
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
        from core.middleware import is_system_context

        if not self.agencia_id:
            current_agency = get_current_agency()
            if current_agency:
                self.agencia = current_agency
            else:
                user = get_current_user()
                # 🛡️ Seguridad God Mode: Un superusuario NO debería crear registros sin agencia
                # a menos que esté en un contexto de sistema explícito.
                if user and user.is_superuser and not is_system_context():
                    raise PermissionDenied(
                        "God Mode: No puedes crear registros globales. Por favor, selecciona una agencia (impersonación) primero."
                    )

                import sys

                is_test = "pytest" in sys.modules or (
                    "manage.py" in sys.argv and "test" in sys.argv
                )

                if not is_system_context() and not is_test and (not user or not user.is_superuser):
                    raise PermissionDenied("Se requiere una agencia para guardar este registro.")

        # Validación de cruce de datos (Seguridad extra)
        current_context_agency = get_current_agency()
        if (
            self.agencia_id
            and current_context_agency
            and self.agencia_id != current_context_agency.id
        ):
            if not get_current_user() or not get_current_user().is_superuser:
                raise PermissionDenied("No puedes guardar datos en otra agencia.")

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Previene borrar datos de otra agencia y aplica soft delete si el modelo lo soporta."""
        if self.agencia_id and get_current_agency() and self.agencia_id != get_current_agency().id:
            if not get_current_user().is_superuser:
                raise PermissionDenied("No puedes borrar datos de otra agencia.")

        if hasattr(self, "is_deleted"):
            # Si tiene el mixin de soft delete, aplicamos lógica de Mixin
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=["is_deleted", "deleted_at"])
        else:
            # Borrado físico normal
            super().delete(*args, **kwargs)

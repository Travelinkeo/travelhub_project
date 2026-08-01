import sys

from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils import timezone

from core.middleware import get_current_agency, get_current_user

# 🛡️ P2-006: Constantes de módulo para evitar re-evaluar sys.argv en cada query al DB
# Estas se evalúan UNA VEZ al importar el módulo, no en cada llamada a get_queryset().
_IS_PYTEST = "pytest" in sys.modules
_IS_MANAGEMENT_COMMAND = bool(
    sys.argv
    and sys.argv[0].endswith("manage.py")
    and any(arg in sys.argv for arg in ["makemigrations", "migrate", "shell", "check", "test"])
)


class SaasQuerySet(models.QuerySet):
    """
    QuerySet personalizado para forzar la inyección de la agencia en operaciones bulk.
    """

    def update(self, **kwargs):
        """update."""
        from core.middleware import get_current_agency, get_current_user, is_system_context

        user = get_current_user()
        if not is_system_context() and not (user and user.is_superuser):
            agency = get_current_agency()
            if agency:
                kwargs["agencia"] = agency
        return super().update(**kwargs)

    def bulk_create(self, objs, **kwargs):
        """bulk_create."""
        from core.middleware import get_current_agency, get_current_user, is_system_context

        user = get_current_user()
        if not is_system_context() and not (user and user.is_superuser):
            agency = get_current_agency()
            if agency:
                for obj in objs:
                    obj.agencia = agency
        return super().bulk_create(objs, **kwargs)


class AgenciaManager(models.Manager):
    """
    Manager Maestro: Filtra automáticamente por Agencia y soft-delete.

    ⚠️  REGLA ABSOLUTA  ⚠️
    Este manager NUNCA expone registros con agencia=null a usuarios de tenant.
    Los registros globales se modelan con FK manual a Agencia (no AgenciaMixin)
    y usan sus propios managers que explícitamente incluyen Q(agencia__isnull=True)
    cuando corresponde (NotificationTemplate, FeatureFlag, AuditLog).

    Si un modelo necesita datos globales compartidos entre agencias, NO debe
    heredar AgenciaMixin. Debe tener un agencia FK manual (nullable) con su
    propio manager que gestione explícitamente el filtro.
    """

    def get_queryset(self):
        """get_queryset."""
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
            # 🛡️ SOLO registros de la agencia. NUNCA agencia=null.
            # Los registros globales no pertenecen a modelos con AgenciaMixin.
            return queryset.filter(agencia=agency)

        # Caso B: No hay agencia pero es un SUPERUSER (God Mode Global)
        if user and user.is_superuser:
            return queryset

        # Caso C: Comandos de gestión (Migrations, Shell, etc.)
        # Usar constantes de módulo — evita parsear sys.argv en cada query (P2-006)
        if _IS_PYTEST or _IS_MANAGEMENT_COMMAND:
            return queryset

        # Caso D: Seguridad por defecto
        return queryset.none()


class GlobalAwareAgenciaManager(AgenciaManager):
    """
    Manager para modelos con FK a Agencia nullable que SÍ necesitan
    exponer registros globales (agencia=null) a todos los tenants.

    EJEMPLOS DE USO:
      - NotificationTemplate (plantillas globales con fallback por agencia)
      - NotificationLog (logs que pueden ser globales o por agencia)
      - NotificationPreference (preferencias globales del sistema)

    Estos modelos NO heredan AgenciaMixin (tienen FK manual a Agencia).
    Úsalo SOLO cuando el diseño explícitamente requiera datos compartidos.
    """

    def get_queryset(self):
        """get_queryset."""
        from core.middleware import is_system_context

        queryset = SaasQuerySet(self.model, using=self._db)

        if is_system_context():
            return queryset

        agency = get_current_agency()
        user = get_current_user()

        if agency:
            return queryset.filter(models.Q(agencia=agency) | models.Q(agencia__isnull=True))

        if user and user.is_superuser:
            return queryset

        if _IS_PYTEST or _IS_MANAGEMENT_COMMAND:
            return queryset

        return queryset.none()


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet que permite operaciones bulk respetando soft-delete."""

    def delete(self):
        """delete."""
        self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        """hard_delete."""
        super().delete()

    def restore(self):
        """restore."""
        self.update(is_deleted=False, deleted_at=None)


class SoftDeleteManager(models.Manager):
    """Manager que retorna SoftDeleteQuerySet sin filtrar is_deleted."""

    def get_queryset(self):
        """get_queryset."""
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

    NOTA ARQUITECTURA:
        Cuando un modelo hereda AgenciaMixin, ``MiModelo.objects`` es un
        ``AgenciaManager`` que filtra automáticamente todas las querysets por
        el contexto de agencia activo (``agency_var`` del middleware). Por lo
        tanto, ``MiModelo.objects.all()`` en vistas/servicios NO retorna todos
        los registros a nivel global, sino sólo los del inquilino actual
        (excepto superuser / system_context / manage.py).

        Las 4 capas de defensa multi-tenant (defense-in-depth) en TravelHub:
          1. ``AgenciaManager.get_queryset()`` (este archivo) — filtra a nivel
             manager. Aplica a TODO ``Model.objects.*`` automáticamente.
          2. ``TenantViewSetMixin`` (core/api/mixins/tenant.py) — sobrescribe
             ``ViewSet.get_queryset()`` para DRF. Defense-in-depth sobre la #1.
          3. ``SaaSMixin`` — equivalente para Django CBV (ListView/DetailView).
          4. ``get_agencia_from_request`` / ``get_object_tenant_or_404``
             (core/security.py) — helpers para vistas funcionales que aplican
             el candado de agencia + 404 tenant-safe.
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


class AgenciaMixinStubs(AgenciaMixin):
    """
    Variante de AgenciaMixin para modelos unmanaged (stubs) que mapean tablas
    legacy donde la FK ``agencia`` está declarada con ``on_delete=DO_NOTHING``
    y la columna ``agencia_id`` ya existe en la tabla (sin migraciones Django).

    Hereda toda la lógica de AgenciaMixin (AgenciaManager + save() + delete())
    pero usa ``DO_NOTHING`` para no romper las constraints existentes en BD.

    USO: Solo para ``apps/finance/models_stubs.py`` y similares donde Django
    no gestiona el esquema (managed=False).
    """

    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.DO_NOTHING,
        related_name="%(class)s_stub_items",
        null=True,
        blank=True,
        db_index=True,
    )

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

                is_test = _IS_PYTEST or _IS_MANAGEMENT_COMMAND

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

"""
core/db_router.py — Router de Base de Datos Multi-instancia.

Enruta lecturas a la réplica de solo-lectura y escrituras al primary.
Permite escalar horizontalmente las queries pesadas de reportes y dashboards
sin afectar el rendimiento de las escrituras.

Configuración en settings.py:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL),         # Primary (lectura/escritura)
        "replica": dj_database_url.parse(DATABASE_REPLICA_URL), # Réplica (solo lectura)
    }
    DATABASE_ROUTERS = ["core.db_router.PrimaryReplicaRouter"]

En Docker (docker-compose.prod.yml), añadir un servicio postgres-replica
con streaming replication desde el primary.

Para usar la réplica explícitamente en un QuerySet específico:
    ventas = Venta.objects.using("replica").filter(agencia=agencia)
"""

import logging

logger = logging.getLogger(__name__)


class PrimaryReplicaRouter:
    """
    Router que dirige lecturas a la réplica y escrituras al primary.

    Comportamiento:
    - Lecturas (SELECT): réplica si está disponible, primary como fallback.
    - Escrituras (INSERT/UPDATE/DELETE): siempre al primary.
    - Migraciones: siempre al primary.
    - Tests: usa 'default' como espejo de 'replica' para no necesitar 2 DBs en CI.
    """

    # Apps que siempre leen del primary (datos críticos o recién escritos)
    # Añadir aquí apps que requieran consistencia lectura-escritura inmediata
    PRIMARY_ONLY_APPS = {
        "axes",  # Login tracking — debe ser inmediatamente consistente
        "sessions",  # Sesiones de usuario
        "admin",  # Django admin
    }

    def db_for_read(self, model, **hints):
        """Dirige lecturas a la réplica, excepto para apps críticas."""
        app_label = model._meta.app_label
        if app_label in self.PRIMARY_ONLY_APPS:
            return "default"
        return "replica"

    def db_for_write(self, model, **hints):
        """Todas las escrituras van al primary."""
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Permite relaciones entre objetos de ambas bases de datos."""
        db_set = {"default", "replica"}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Las migraciones solo se ejecutan en el primary."""
        return db == "default"

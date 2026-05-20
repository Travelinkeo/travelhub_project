import logging

logger = logging.getLogger(__name__)

class MigrationService:
    """
    Service layer to explicitly orchestrate migration check operations,
    completely decoupled from implicit signals.
    """

    @staticmethod
    def trigger_migration_alert_if_needed(migration_check, created):
        """
        Dispatches a migration alert notification if the result level is critical.
        """
        if created and migration_check.alert_level in ['RED', 'YELLOW']:
            try:
                from apps.communications.services.notification_service import notificar_alerta_migratoria
                notificar_alerta_migratoria(migration_check)
                logger.info(f"🚨 MigrationService: Dispatched migration alert for check {migration_check.pk}")
                return True
            except Exception as e:
                logger.error(f"Error in MigrationService.trigger_migration_alert_if_needed: {e}")
        return False

"""Tests para tareas de Celery — corregido para reflejar las tareas reales."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import override_settings


@pytest.mark.django_db
class TestCeleryTasks:
    """Tests para tareas asíncronas reales de core.tasks."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
    def test_parsear_boleto_individual_no_falla_con_id_invalido(self):
        """La tarea de parseo debe manejar IDs inválidos sin crashear el worker."""
        from core.tasks import parsear_boleto_individual
        try:
            parsear_boleto_individual(boleto_id=99999)
            assert True  # Llegó aquí sin excepción
        except Exception as e:
            pytest.fail(f"parsear_boleto_individual crasheó con ID inválido: {e}")

    @patch("core.tasks.parsear_boleto_individual")
    def test_retry_queued_boletos_es_invocable(self, mock_task):
        """retry_queued_boletos debe poder ejecutarse sin errores de setup."""
        from core.tasks import retry_queued_boletos
        try:
            retry_queued_boletos()
            assert True
        except Exception as e:
            pytest.fail(f"retry_queued_boletos fallo: {e}")

    @patch("core.tasks.send_ticket_notification")
    def test_send_ticket_notification_existe(self, mock_notify):
        """Verifica que la tarea de notificación existe y es callable."""
        from core.tasks import send_ticket_notification
        assert callable(send_ticket_notification)

    def test_sync_bcv_rates_existe(self):
        """Verifica que la tarea de sincronización de tasas BCV existe."""
        from core.tasks import sync_bcv_rates
        assert callable(sync_bcv_rates)

    def test_check_pending_payments_existe(self):
        """Verifica que la tarea de pagos pendientes existe."""
        from core.tasks import check_pending_payments
        assert callable(check_pending_payments)

    @patch("core.tasks.process_incoming_emails")
    def test_process_incoming_emails_invocable(self, mock_task):
        """La tarea de correos entrantes existe y es callable."""
        from core.tasks import process_incoming_emails
        assert callable(process_incoming_emails)

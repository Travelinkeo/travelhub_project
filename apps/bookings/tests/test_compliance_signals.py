from datetime import date, datetime
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.bookings.models import SegmentoVuelo, Venta
from apps.bookings.tasks import verificar_cumplimiento_pasaportes_reserva_task
from apps.crm.models import Pasajero


@pytest.mark.django_db
class TestComplianceAndSignals:
    @patch("apps.bookings.tasks.requests.post")
    def test_compliance_guard_detecta_pasaporte_proximo_a_vencer(
        self, mock_post, agencia_premium, settings
    ):
        """El Compliance Guard debe alertar a Telegram si el pasaporte vence en menos de 6 meses."""

        # Configurar variables de entorno de Telegram
        settings.TELEGRAM_BOT_TOKEN = "dummy_token"
        settings.TELEGRAM_OPERACIONES_CHAT_ID = "dummy_chat_id"

        # Configurar mock para simular respuesta exitosa de la API de Telegram
        mock_post.return_value.status_code = 200

        venta = Venta.objects.create(
            localizador="VEN666", agencia=agencia_premium, subtotal=100, fecha_venta=timezone.now()
        )

        # Trip date: October 1, 2026
        trip_date = timezone.make_aware(datetime(2026, 10, 1, 10, 0, 0))
        SegmentoVuelo.objects.create(venta=venta, agencia=agencia_premium, fecha_salida=trip_date)

        # Pasaporte vence en una fecha crítica (menos de 6 meses desde el viaje)
        pasaporte_vencido_critico = date(2026, 11, 15)

        pasajero = Pasajero.objects.create(
            apellidos="Perez",
            nombres="Juan",
            agencia=agencia_premium,
            fecha_vencimiento_pasaporte=pasaporte_vencido_critico,
        )
        venta.pasajeros.add(pasajero)

        # Invocamos manualmente la tarea que las señales o el parser ejecutan en background
        resultado = verificar_cumplimiento_pasaportes_reserva_task(venta.pk)

        assert "Alertas: 1" in resultado
        # Certificamos que el sistema ejecutó la petición POST proactiva hacia el bot de Telegram
        assert mock_post.called is True

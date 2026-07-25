"""Tests para modelos de communications app (cobertura faltante)"""

import pytest
from django.db.utils import IntegrityError

from apps.communications.models.monitor_log import EmailMonitorLog
from apps.communications.models.notifications import (
    NotificationLog,
    NotificationPreference,
    NotificationTemplate,
)
from apps.communications.models.provider import ComunicacionProveedor
from apps.communications.models.push_subscription import PushSubscription


@pytest.mark.django_db
class TestNotificationPreference:
    """Test Notification Preference."""
    def test_crear_preferencia(self, usuario_staff, agencia_premium):
        """Crear preferencia."""
        pref = NotificationPreference.objects.create(
            user=usuario_staff,
            agencia=agencia_premium,
            event_type="venta_creada",
            channel="email",
            enabled=True,
        )
        assert pref.pk is not None
        assert (
            str(pref)
            == f"{usuario_staff.username} - venta_creada - email - {agencia_premium.nombre}"
        )

    def test_unique_together(self, usuario_staff, agencia_premium):
        """Unique together."""
        NotificationPreference.objects.create(
            user=usuario_staff,
            agencia=agencia_premium,
            event_type="venta_creada",
            channel="email",
        )
        with pytest.raises(IntegrityError):
            NotificationPreference.objects.create(
                user=usuario_staff,
                agencia=agencia_premium,
                event_type="venta_creada",
                channel="email",
            )

    def test_preferencia_sin_agencia(self, usuario_staff):
        """Preferencia sin agencia."""
        pref = NotificationPreference.objects.create(
            user=usuario_staff,
            agencia=None,
            event_type="venta_creada",
            channel="push",
        )
        assert str(pref) == f"{usuario_staff.username} - venta_creada - push"

    def test_preferencia_default_enabled(self, usuario_staff, agencia_premium):
        """Preferencia default enabled."""
        pref = NotificationPreference.objects.create(
            user=usuario_staff,
            agencia=agencia_premium,
            event_type="pago_confirmado",
            channel="whatsapp",
        )
        assert pref.enabled is True


@pytest.mark.django_db
class TestNotificationTemplate:
    """Test Notification Template."""
    def test_crear_plantilla(self):
        """Crear plantilla."""
        tmpl = NotificationTemplate.objects.create(
            name="venta_confirmacion",
            event_type="venta_creada",
            channel="email",
            subject_template="Confirmación de venta {{localizador}}",
            body_template="Hola {{cliente}}, tu venta {{localizador}} está confirmada.",
        )
        assert tmpl.pk is not None
        assert str(tmpl) == "venta_confirmacion (email - es)"

    def test_render_body_simple(self):
        """Render body simple."""
        tmpl = NotificationTemplate.objects.create(
            name="test",
            event_type="test_event",
            channel="email",
            body_template="Hola {{nombre}}, tu código es {{codigo}}",
        )
        result = tmpl.render({"nombre": "Juan", "codigo": "ABC123"})
        assert result["body"] == "Hola Juan, tu código es ABC123"

    def test_render_missing_variable(self):
        """Render missing variable."""
        tmpl = NotificationTemplate.objects.create(
            name="test",
            event_type="test_event",
            channel="email",
            body_template="Hola {{nombre}}, tu código es {{codigo}}",
        )
        result = tmpl.render({"nombre": "Juan"})
        assert "{{codigo}}" in result["body"]

    def test_render_subject(self):
        """Render subject."""
        tmpl = NotificationTemplate.objects.create(
            name="test",
            event_type="test_event",
            channel="email",
            subject_template="Notificación para {{usuario}}",
            body_template="Cuerpo",
        )
        result = tmpl.render({"usuario": "admin"})
        assert result["subject"] == "Notificación para admin"

    def test_render_html(self):
        """Render html."""
        tmpl = NotificationTemplate.objects.create(
            name="test",
            event_type="test_event",
            channel="email",
            body_template="Cuerpo",
            html_template="<h1>Hola {{nombre}}</h1><p>Mensaje</p>",
        )
        result = tmpl.render({"nombre": "María"})
        assert "<h1>Hola María</h1>" in result["html"]
        assert "<p>Mensaje</p>" in result["html"]

    def test_render_empty_subject(self):
        """Render empty subject."""
        tmpl = NotificationTemplate.objects.create(
            name="test",
            event_type="test_event",
            channel="email",
            body_template="Cuerpo",
        )
        result = tmpl.render({"var": "val"})
        assert result["subject"] == ""

    def test_is_default_flag(self):
        """Is default flag."""
        tmpl = NotificationTemplate.objects.create(
            name="default_template",
            event_type="test_event",
            channel="email",
            body_template="Default",
            is_default=True,
        )
        assert tmpl.is_default is True

    def test_agencia_scoped_template(self, agencia_premium):
        """Agencia scoped template."""
        tmpl = NotificationTemplate.objects.create(
            name="agencia_template",
            event_type="test_event",
            channel="whatsapp",
            body_template="Plantilla para {{agencia}}",
            agencia=agencia_premium,
        )
        assert tmpl.agencia == agencia_premium

    def test_render_complex_variables(self):
        """Render complex variables."""
        tmpl = NotificationTemplate.objects.create(
            name="complex",
            event_type="test_event",
            channel="email",
            body_template="Destino: {{destino}}, Pasajeros: {{pasajeros}}, Total: ${{total}}",
        )
        result = tmpl.render({"destino": "Miami", "pasajeros": "2", "total": "500.00"})
        assert result["body"] == "Destino: Miami, Pasajeros: 2, Total: $500.00"


@pytest.mark.django_db
class TestNotificationLog:
    """Test Notification Log."""
    def test_crear_log(self):
        """Crear log."""
        log = NotificationLog.objects.create(
            event_type="venta_creada",
            channel="email",
            recipient="test@example.com",
            body="Cuerpo del mensaje",
            status="sent",
        )
        assert log.pk is not None
        assert str(log) == "venta_creada -> test@example.com (sent)"

    def test_log_default_status(self):
        """Log default status."""
        log = NotificationLog.objects.create(
            event_type="venta_creada",
            channel="whatsapp",
            recipient="+1234567890",
            body="Mensaje",
        )
        assert log.status == "pending"

    def test_log_with_error(self):
        """Log with error."""
        log = NotificationLog.objects.create(
            event_type="venta_creada",
            channel="email",
            recipient="test@example.com",
            body="Mensaje",
            status="failed",
            error_message="Connection timeout",
            retry_count=2,
        )
        assert log.status == "failed"
        assert log.retry_count == 2


@pytest.mark.django_db
class TestEmailMonitorLog:
    """Test Email Monitor Log."""
    def test_crear_monitor_log(self, agencia_premium):
        """Crear monitor log."""
        log = EmailMonitorLog.objects.create(
            agencia=agencia_premium,
            estado=EmailMonitorLog.Estado.SUCCESS,
            mensaje="Correos procesados exitosamente",
            correos_procesados=5,
            tiempo_ejecucion=3.5,
        )
        assert log.pk is not None
        assert log.correos_procesados == 5
        assert agencia_premium.nombre in str(log)

    def test_monitor_log_default_estado(self, agencia_premium):
        """Monitor log default estado."""
        log = EmailMonitorLog.objects.create(
            agencia=agencia_premium,
            mensaje="Log sin estado explícito",
        )
        assert log.estado == EmailMonitorLog.Estado.SUCCESS

    def test_monitor_log_error_state(self, agencia_premium):
        """Monitor log error state."""
        log = EmailMonitorLog.objects.create(
            agencia=agencia_premium,
            estado=EmailMonitorLog.Estado.ERROR,
            mensaje="Conexión IMAP fallida",
            host_conectado="imap.example.com",
        )
        assert log.host_conectado == "imap.example.com"
        assert log.get_estado_display() == "Error"


@pytest.mark.django_db
class TestComunicacionProveedor:
    """Test Comunicacion Proveedor."""
    def test_crear_comunicacion(self, agencia_premium):
        """Crear comunicacion."""
        com = ComunicacionProveedor.objects.create(
            agencia=agencia_premium,
            remitente="reservas@aerolinea.com",
            asunto="E-Ticket Confirmación - ABC123",
            categoria=ComunicacionProveedor.Categoria.TICKET,
            message_id="msg-001",
        )
        assert com.pk is not None
        assert com.categoria == "TICKET"
        assert str(com) == "reservas@aerolinea.com - E-Ticket Confirmación - ABC123..."

    def test_comunicacion_default_categoria(self, agencia_premium):
        """Comunicacion default categoria."""
        com = ComunicacionProveedor.objects.create(
            agencia=agencia_premium,
            remitente="test@test.com",
            asunto="Mensaje general",
        )
        assert com.categoria == ComunicacionProveedor.Categoria.OTHER

    def test_comunicacion_con_contenido_extraido(self, agencia_premium):
        """Comunicacion con contenido extraido."""
        com = ComunicacionProveedor.objects.create(
            agencia=agencia_premium,
            remitente="alerts@aerolinea.com",
            asunto="Cambio de itinerario",
            categoria=ComunicacionProveedor.Categoria.ALERT,
            contenido_extraido={"vuelo": "AV123", "nuevo_horario": "14:30"},
            procesado=True,
        )
        assert com.contenido_extraido["vuelo"] == "AV123"
        assert com.procesado is True

    def test_unique_message_id(self, agencia_premium):
        """Unique message id."""
        ComunicacionProveedor.objects.create(
            agencia=agencia_premium,
            remitente="test@test.com",
            asunto="Test",
            message_id="unique-msg",
        )
        with pytest.raises(IntegrityError):
            ComunicacionProveedor.objects.create(
                agencia=agencia_premium,
                remitente="test@test.com",
                asunto="Test",
                message_id="unique-msg",
            )


@pytest.mark.django_db
class TestPushSubscription:
    """Test Push Subscription."""
    def test_crear_suscripcion(self, usuario_staff):
        """Crear suscripcion."""
        sub = PushSubscription.objects.create(
            user=usuario_staff,
            endpoint="https://push.example.com/endpoint-abc",
            auth_key="auth_key_123",
            p256dh_key="p256dh_key_456",
            user_agent="Mozilla/5.0",
        )
        assert sub.pk is not None
        assert sub.active is True
        assert str(sub) == f"PushSubscription({usuario_staff.id})"

    def test_subscription_default_active(self, usuario_staff):
        """Subscription default active."""
        sub = PushSubscription.objects.create(
            user=usuario_staff,
            endpoint="https://push.example.com/endpoint-def",
            auth_key="auth1",
            p256dh_key="p256dh1",
        )
        assert sub.active is True

    def test_unique_endpoint(self, usuario_staff):
        """Unique endpoint."""
        PushSubscription.objects.create(
            user=usuario_staff,
            endpoint="https://push.example.com/endpoint-ghi",
            auth_key="auth1",
            p256dh_key="p256dh1",
        )
        with pytest.raises(IntegrityError):
            PushSubscription.objects.create(
                user=usuario_staff,
                endpoint="https://push.example.com/endpoint-ghi",
                auth_key="auth2",
                p256dh_key="p256dh2",
            )


@pytest.mark.django_db
class TestLeadModel:
    """Test Lead Model."""
    def test_crear_lead(self):
        """Crear lead."""
        from apps.communications.models.lead import Lead

        lead = Lead.objects.create(email="test@example.com", nombre="Test")
        assert lead.pk is not None
        assert str(lead) == "test@example.com"
        assert lead.fuente == "landing_page"
        assert lead.guia_descargada is False

    def test_lead_unique_email(self):
        """Lead unique email."""
        from apps.communications.models.lead import Lead

        Lead.objects.create(email="dup@example.com")
        with pytest.raises(IntegrityError):
            Lead.objects.create(email="dup@example.com")

    def test_lead_ordering(self):
        """Lead ordering."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.communications.models.lead import Lead

        l1 = Lead.objects.create(email="first@example.com")
        l2 = Lead.objects.create(email="second@example.com")
        Lead.objects.filter(pk=l1.pk).update(created_at=timezone.now() - timedelta(hours=1))
        leads = Lead.objects.all()
        assert leads[0] == l2
        assert leads[1] == l1

    def test_lead_default_fields(self):
        """Lead default fields."""
        from apps.communications.models.lead import Lead

        lead = Lead.objects.create(email="defaults@example.com")
        assert lead.nombre == ""
        assert lead.ip_origen == ""
        assert lead._followup_1_sent is False
        assert lead._followup_2_sent is False

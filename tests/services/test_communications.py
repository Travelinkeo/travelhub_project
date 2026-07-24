"""Tests para servicios de comunicación — email, WhatsApp, notificaciones."""

import unittest.mock

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.services]


class TestEmailUnified:
    def test_send_email_basic(self, monkeypatch):
        mock_send = unittest.mock.MagicMock(return_value={"id": "mock-email-id"})
        monkeypatch.setattr(
            "apps.communications.services.email_unified.resend.Emails.send",
            mock_send,
        )
        from apps.communications.services.email_unified import send_email

        result = send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Hello</p>",
        )
        assert result is not None


class TestWhatsAppUnified:
    def test_send_whatsapp_message(self, monkeypatch):
        mock_send = unittest.mock.MagicMock(return_value={"messages": [{"id": "wam-id"}]})
        monkeypatch.setattr(
            "apps.communications.services.whatsapp_unified.requests.post",
            mock_send,
        )
        from apps.communications.services.whatsapp_unified import send_whatsapp

        result = send_whatsapp("+584121234567", "Test message")
        assert result is not None


class TestNotificationService:
    def test_create_notification(self, db):
        from apps.communications.models.notifications import Notification

        notification = Notification.objects.create(
            title="Test Notification",
            message="This is a test",
            notification_type="INFO",
        )
        assert notification.id is not None
        assert str(notification) is not None

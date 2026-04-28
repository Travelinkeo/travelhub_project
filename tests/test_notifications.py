"""Tests para sistema de notificaciones"""
import pytest
from unittest.mock import Mock, patch
from core.notifications import EmailChannel, WhatsAppChannel, NotificationService


class TestEmailChannel:
    """Tests para EmailChannel"""
    
    def test_is_available_with_email_configured(self, settings):
        settings.EMAIL_HOST_USER = 'test@example.com'
        channel = EmailChannel()
        assert channel.is_available() is True
    
    def test_is_available_without_email(self, settings):
        settings.EMAIL_HOST_USER = ''
        channel = EmailChannel()
        assert channel.is_available() is False
    
    @patch('core.notifications.channels.enviar_email_generico')
    def test_send_email_success(self, mock_email):
        mock_email.return_value = True
        channel = EmailChannel()
        result = channel.send('test@example.com', 'Test message', subject='Test')
        assert result is True
        mock_email.assert_called_once()
    
    @patch('core.notifications.channels.enviar_email_generico')
    def test_send_email_failure(self, mock_email):
        mock_email.side_effect = Exception('Email error')
        channel = EmailChannel()
        result = channel.send('test@example.com', 'Test message')
        assert result is False


class TestWhatsAppChannel:
    """Tests para WhatsAppChannel"""
    
    def test_is_available_enabled(self, settings):
        settings.WHATSAPP_NOTIFICATIONS_ENABLED = True
        channel = WhatsAppChannel()
        assert channel.is_available() is True
    
    def test_is_available_disabled(self, settings):
        settings.WHATSAPP_NOTIFICATIONS_ENABLED = False
        channel = WhatsAppChannel()
        assert channel.is_available() is False
    
    @patch('core.notifications.channels.enviar_whatsapp')
    def test_send_whatsapp_success(self, mock_whatsapp):
        mock_whatsapp.return_value = True
        channel = WhatsAppChannel()
        result = channel.send('+1234567890', 'Test message')
        assert result is True
    
    @patch('core.notifications.channels.enviar_whatsapp')
    def test_send_whatsapp_failure(self, mock_whatsapp):
        mock_whatsapp.side_effect = Exception('WhatsApp error')
        channel = WhatsAppChannel()
        result = channel.send('+1234567890', 'Test message')
        assert result is False


class TestNotificationService:
    """Tests para NotificationService"""
    
    @patch('core.notifications.service.EmailChannel')
    @patch('core.notifications.service.WhatsAppChannel')
    def test_notify_both_channels(self, mock_whatsapp_class, mock_email_class):
        # Setup mocks
        mock_email = Mock()
        mock_email.is_available.return_value = True
        mock_email.send.return_value = True
        mock_email_class.return_value = mock_email
        
        mock_whatsapp = Mock()
        mock_whatsapp.is_available.return_value = True
        mock_whatsapp.send.return_value = True
        mock_whatsapp_class.return_value = mock_whatsapp
        
        # Test
        service = NotificationService()
        recipient = {'email': 'test@example.com', 'telefono': '+1234567890'}
        results = service.notify('confirmacion_venta', recipient, {'venta': Mock()})
        
        assert results['email'] is True
        assert results['whatsapp'] is True
    
    def test_get_recipient_for_channel_email(self):
        service = NotificationService()
        recipient = {'email': 'test@example.com', 'telefono': '+1234567890'}
        result = service._get_recipient_for_channel(recipient, 'email')
        assert result == 'test@example.com'
    
    def test_get_recipient_for_channel_whatsapp(self):
        service = NotificationService()
        recipient = {'email': 'test@example.com', 'telefono': '+1234567890'}
        result = service._get_recipient_for_channel(recipient, 'whatsapp')
        assert result == '+1234567890'

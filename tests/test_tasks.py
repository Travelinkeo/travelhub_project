"""Tests para tareas de Celery"""
import pytest
from unittest.mock import Mock, patch, mock_open
from core.tasks import process_ticket_async, generate_pdf_async, send_notification_async


class TestCeleryTasks:
    """Tests para tareas asíncronas"""
    
    @patch('core.tasks.orquestar_parseo_de_boleto')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test data')
    def test_process_ticket_async_success(self, mock_file, mock_parser):
        """Test procesamiento exitoso de boleto"""
        mock_parser.return_value = ({'SOURCE_SYSTEM': 'SABRE'}, 'Success')
        
        result = process_ticket_async('test.pdf')
        
        assert result['success'] is True
        assert 'data' in result
        mock_parser.assert_called_once()
    
    @patch('core.tasks.orquestar_parseo_de_boleto')
    @patch('builtins.open', new_callable=mock_open)
    def test_process_ticket_async_failure(self, mock_file, mock_parser):
        """Test fallo en procesamiento"""
        mock_parser.return_value = (None, 'Error parsing')
        
        result = process_ticket_async('test.pdf')
        
        assert result['success'] is False
        assert 'error' in result
    
    @patch('core.tasks.generate_ticket')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_generate_pdf_async_success(self, mock_makedirs, mock_file, mock_generate):
        """Test generación exitosa de PDF"""
        mock_generate.return_value = (b'PDF content', 'test.pdf')
        
        result = generate_pdf_async({'SOURCE_SYSTEM': 'SABRE'})
        
        assert result == 'test.pdf'
        mock_generate.assert_called_once()
    
    @patch('core.tasks.generate_ticket')
    def test_generate_pdf_async_failure(self, mock_generate):
        """Test fallo en generación de PDF"""
        mock_generate.side_effect = Exception('PDF error')
        
        result = generate_pdf_async({'SOURCE_SYSTEM': 'SABRE'})
        
        assert result is None
    
    @patch('core.tasks.notification_service')
    def test_send_notification_async_success(self, mock_service):
        """Test envío exitoso de notificación"""
        mock_service.notify.return_value = {'email': True, 'whatsapp': True}
        
        result = send_notification_async(
            'confirmacion_venta',
            {'email': 'test@example.com'},
            {'venta': Mock()}
        )
        
        assert result['email'] is True
        assert result['whatsapp'] is True
    
    @patch('core.tasks.notification_service')
    def test_send_notification_async_failure(self, mock_service):
        """Test fallo en envío de notificación"""
        mock_service.notify.side_effect = Exception('Notification error')
        
        result = send_notification_async('test', {}, {})
        
        assert 'error' in result

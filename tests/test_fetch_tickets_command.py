import imaplib
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings


class FetchTicketsCommandTest(TestCase):

    @override_settings(GMAIL_USER=None, GMAIL_APP_PASSWORD=None)
    def test_missing_credentials(self):
        """
        Verifica que el comando termina limpiamente si faltan las credenciales de correo.
        """
        out = StringIO()
        err = StringIO()
        call_command('fetch_tickets', stdout=out, stderr=err)
        
        self.assertIn("Error Crítico: Las variables de entorno GMAIL_USER y GMAIL_APP_PASSWORD no están configuradas", out.getvalue())
        self.assertEqual(err.getvalue(), '') # No debería haber un error de CommandError

    @patch('imaplib.IMAP4_SSL')
    @override_settings(GMAIL_USER='test@gmail.com', GMAIL_APP_PASSWORD='fakepass')
    def test_imap_login_fails(self, mock_imap_ssl):
        """
        Verifica que el comando maneja un fallo en el login de IMAP.
        """
        # Configurar el mock para que falle en el login
        mock_instance = mock_imap_ssl.return_value
        mock_instance.login.side_effect = imaplib.IMAP4.error("Login failed")

        out = StringIO()
        err = StringIO()
        call_command('fetch_tickets', stdout=out, stderr=err)

        self.assertIn("Ocurrió un error crítico general: Login failed", out.getvalue())
        self.assertEqual(err.getvalue(), '')

    @patch('imaplib.IMAP4_SSL')
    @override_settings(GMAIL_USER='test@gmail.com', GMAIL_APP_PASSWORD='fakepass', GMAIL_FROM_KIU='test@kiu.com')
    def test_no_new_emails(self, mock_imap_ssl):
        """
        Verifica el comportamiento cuando no hay correos nuevos.
        """
        mock_instance = mock_imap_ssl.return_value
        mock_instance.login.return_value = ('OK', [b'Login successful'])
        mock_instance.select.return_value = ('OK', [b'1'])
        # Simular que no se encuentran correos
        mock_instance.search.return_value = ('OK', [b''])

        out = StringIO()
        call_command('fetch_tickets', stdout=out)

        self.assertIn("No se encontraron nuevos correos para procesar.", out.getvalue())
        mock_instance.logout.assert_called_once()
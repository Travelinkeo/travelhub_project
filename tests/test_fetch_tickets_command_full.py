from types import SimpleNamespace

import pytest
from django.core.management import call_command


class DummyMailSuccess:
    def __init__(self, subject='E-TICKET ITINERARY RECEIPT TEST', body=b'RawEmailBytes'):
        self._subject = subject
        self._body = body
        self.logged_out = False
        self.seen_flags = []
        self.selected_box = None
    def login(self, user, password):
        return 'OK', []
    def select(self, box):
        self.selected_box = box
        return 'OK', []
    def search(self, charset, criteria):
        # Return a single unread email id '1'
        return 'OK', [b'1']
    def fetch(self, email_id, params):
        # Minimal RFC822 with Subject header
        raw = b'Subject: ' + self._subject.encode('utf-8') + b'\r\n\r\n' + self._body
        return 'OK', [(None, raw)]
    def store(self, email_id, flags, value):
        self.seen_flags.append((email_id, value))
        return 'OK', []
    def logout(self):
        self.logged_out = True
        return 'BYE', []

class DummyMailFetchError(DummyMailSuccess):
    def fetch(self, email_id, params):  # simulate fetch failure
        return 'NO', []

class DummyMailRaise(DummyMailSuccess):
    def search(self, charset, criteria):
        raise RuntimeError('Injected failure in search')

@pytest.mark.django_db
def test_fetch_tickets_success(monkeypatch, settings, tmp_path):
    settings.GMAIL_USER = 'user@example.com'
    settings.GMAIL_APP_PASSWORD = 'app-pass'
    settings.GMAIL_FROM_KIU = 'noreply@kiusys.com'

    dummy_mail = DummyMailSuccess()
    monkeypatch.setattr('core.management.commands.fetch_tickets.imaplib.IMAP4_SSL', lambda host: dummy_mail)

    # Intercept BoletoImportado to avoid heavy logic if present
    from core.management.commands import fetch_tickets as module
    class DummyBoleto:  # minimal stub with file save API
        def __init__(self):
            self.id_boleto_importado = 123
            self.archivo_boleto = SimpleNamespace(save=lambda filename, content, save=True: None)
    monkeypatch.setattr(module, 'BoletoImportado', DummyBoleto)

    call_command('fetch_tickets')
    # Assert it marked as seen
    assert any(eid == b'1' for eid, _ in dummy_mail.seen_flags)

@pytest.mark.django_db
def test_fetch_tickets_fetch_failure(monkeypatch, settings, capsys):
    settings.GMAIL_USER = 'user@example.com'
    settings.GMAIL_APP_PASSWORD = 'app-pass'

    dummy_mail = DummyMailFetchError()
    monkeypatch.setattr('core.management.commands.fetch_tickets.imaplib.IMAP4_SSL', lambda host: dummy_mail)

    from core.management.commands import fetch_tickets as module
    class DummyBoleto:  # stub - shouldn't be used successfully
        def __init__(self):
            self.id_boleto_importado = 999
            self.archivo_boleto = SimpleNamespace(save=lambda filename, content, save=True: None)
    monkeypatch.setattr(module, 'BoletoImportado', DummyBoleto)

    call_command('fetch_tickets')
    captured = capsys.readouterr()
    assert 'No se pudo obtener el contenido del email ID 1' in captured.out

@pytest.mark.django_db
def test_fetch_tickets_general_exception(monkeypatch, settings, capsys):
    settings.GMAIL_USER = 'user@example.com'
    settings.GMAIL_APP_PASSWORD = 'app-pass'

    dummy_mail = DummyMailRaise()
    monkeypatch.setattr('core.management.commands.fetch_tickets.imaplib.IMAP4_SSL', lambda host: dummy_mail)

    call_command('fetch_tickets')
    captured = capsys.readouterr()
    assert 'Ocurrió un error crítico general' in captured.out

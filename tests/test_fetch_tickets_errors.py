import pytest
from django.core.management import call_command


class DummyMailBase:
    def __init__(self):
        self.actions = []
    def login(self, user, pw):
        self.actions.append(('login', user))
    def select(self, box):
        self.actions.append(('select', box))
        return 'OK', []
    def search(self, *args):
        return 'OK', [b'']
    def logout(self):
        self.actions.append(('logout', None))

class DummyMailNoLogin(DummyMailBase):
    def login(self, user, pw):
        raise RuntimeError('login failed')

class DummyMailOneMessage(DummyMailBase):
    def search(self, *args):
        # return one id
        return 'OK', [b'1']
    def fetch(self, msg_id, spec):
        # Correo con asunto bytes raro
        raw = b"Subject: =?utf-8?b?w6FzdW50byBUZXN0?=\n\nBody"  # asunto "ásunto Test"
        return 'OK', [(None, raw)]
    def store(self, *args):
        self.actions.append(('store', args[0]))

@pytest.mark.django_db
def test_fetch_tickets_missing_credentials(settings, monkeypatch, capsys):
    # Aseguramos ausencia de variables
    for k in ['GMAIL_USER', 'GMAIL_APP_PASSWORD']:
        if hasattr(settings, k):
            delattr(settings, k)
    # Mock IMAP para evitar conexión real
    monkeypatch.setattr('imaplib.IMAP4_SSL', lambda host: DummyMailBase())
    call_command('fetch_tickets')
    out = capsys.readouterr().out
    assert 'no están configuradas' in out.lower()

@pytest.mark.django_db
def test_fetch_tickets_login_error(settings, monkeypatch, capsys):
    settings.GMAIL_USER = 'user@test'
    settings.GMAIL_APP_PASSWORD = 'pwd'
    monkeypatch.setattr('imaplib.IMAP4_SSL', lambda host: DummyMailNoLogin())
    call_command('fetch_tickets')
    out = capsys.readouterr().out
    assert 'login failed' in out

@pytest.mark.django_db
def test_fetch_tickets_no_messages(settings, monkeypatch, capsys):
    settings.GMAIL_USER = 'user@test'
    settings.GMAIL_APP_PASSWORD = 'pwd'
    mail = DummyMailBase()
    monkeypatch.setattr('imaplib.IMAP4_SSL', lambda host: mail)
    call_command('fetch_tickets')
    out = capsys.readouterr().out
    assert 'No se encontraron nuevos correos' in out
    assert ('logout', None) in mail.actions

@pytest.mark.django_db
def test_fetch_tickets_one_message_creates_boleto(settings, monkeypatch, capsys):
    from core.models.boletos import BoletoImportado
    settings.GMAIL_USER = 'user@test'
    settings.GMAIL_APP_PASSWORD = 'pwd'
    mail = DummyMailOneMessage()
    monkeypatch.setattr('imaplib.IMAP4_SSL', lambda host: mail)
    call_command('fetch_tickets')
    out = capsys.readouterr().out
    assert 'Se encontraron 1 correo(s)' in out
    assert BoletoImportado.objects.count() == 1

@pytest.mark.django_db
def test_fetch_tickets_malformed_subject(settings, monkeypatch, capsys):
    """Verifica que un asunto malformado no rompa el comando y se loguee."""
    from core.models.boletos import BoletoImportado

    class DummyMailMalformedSubject(DummyMailBase):
        def search(self, *args):
            return 'OK', [b'1']
        def fetch(self, msg_id, spec):
            # Correo con un header de Subject que podría causar un error
            raw = b"Subject: =?invalid-charset?b?dGVzdA==?=\n\nBody"
            return 'OK', [(None, raw)]
        def store(self, *args):
            self.actions.append(('store', args[0]))

    settings.GMAIL_USER = 'user@test'
    settings.GMAIL_APP_PASSWORD = 'pwd'
    mail = DummyMailMalformedSubject()
    monkeypatch.setattr('imaplib.IMAP4_SSL', lambda host: mail)
    
    call_command('fetch_tickets')
    
    out = capsys.readouterr().out
    assert "error procesando el email" in out.lower()
    assert BoletoImportado.objects.count() == 0
    # Verificar que no se intenta marcar como leído si falla
    assert ('store', b'1') not in mail.actions

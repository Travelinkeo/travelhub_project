import pytest
from django.core.management import call_command


class DummyMailBase:
    """DummyMailBase."""

    def __init__(self):
        """__init__."""
        self.actions = []

    def login(self, user, pw):
        """login."""
        self.actions.append(("login", user))

    def select(self, box):
        """select."""
        self.actions.append(("select", box))
        return "OK", []

    def search(self, *args):
        """search."""
        return "OK", [b""]

    def logout(self):
        """logout."""
        self.actions.append(("logout", None))


class DummyMailNoLogin(DummyMailBase):
    """DummyMailNoLogin."""

    def login(self, user, pw):
        """login."""
        raise RuntimeError("login failed")


class DummyMailOneMessage(DummyMailBase):
    """DummyMailOneMessage."""

    def search(self, *args):
        """search."""
        # return one id
        return "OK", [b"1"]

    def fetch(self, msg_id, spec):
        """fetch."""
        # Correo con asunto bytes raro
        raw = b"Subject: =?utf-8?b?w6FzdW50byBUZXN0?=\n\nBody"  # asunto "ásunto Test"
        return "OK", [(None, raw)]

    def store(self, *args):
        """store."""
        self.actions.append(("store", args[0]))


@pytest.mark.django_db
def test_fetch_tickets_missing_credentials(settings, monkeypatch, capsys):
    """test_fetch_tickets_missing_credentials."""
    # Aseguramos ausencia de variables
    for k in ["GMAIL_USER", "GMAIL_APP_PASSWORD"]:
        if hasattr(settings, k):
            delattr(settings, k)
    # Mock IMAP para evitar conexión real
    monkeypatch.setattr("imaplib.IMAP4_SSL", lambda host: DummyMailBase())
    call_command("fetch_tickets")
    out = capsys.readouterr().out
    assert "no están configuradas" in out.lower()


@pytest.mark.django_db
def test_fetch_tickets_login_error(settings, monkeypatch, capsys):
    """test_fetch_tickets_login_error."""
    settings.GMAIL_USER = "user@test"
    settings.GMAIL_APP_PASSWORD = "pwd"
    monkeypatch.setattr("imaplib.IMAP4_SSL", lambda host: DummyMailNoLogin())
    call_command("fetch_tickets")
    out = capsys.readouterr().out
    assert "login failed" in out


@pytest.mark.django_db
def test_fetch_tickets_no_messages(settings, monkeypatch, capsys):
    """test_fetch_tickets_no_messages."""
    settings.GMAIL_USER = "user@test"
    settings.GMAIL_APP_PASSWORD = "pwd"
    mail = DummyMailBase()
    monkeypatch.setattr("imaplib.IMAP4_SSL", lambda host: mail)
    call_command("fetch_tickets")
    out = capsys.readouterr().out
    assert "No se encontraron nuevos correos" in out
    assert ("logout", None) in mail.actions


@pytest.mark.django_db
def test_fetch_tickets_one_message_creates_boleto(settings, monkeypatch, capsys):
    """test_fetch_tickets_one_message_creates_boleto."""
    from apps.bookings.models import BoletoImportado

    settings.GMAIL_USER = "user@test"
    settings.GMAIL_APP_PASSWORD = "pwd"
    settings.USE_R2 = False
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    mail = DummyMailOneMessage()
    monkeypatch.setattr("imaplib.IMAP4_SSL", lambda host: mail)
    call_command("fetch_tickets")
    out = capsys.readouterr().out
    assert "Se encontraron 1 correo(s)" in out
    assert BoletoImportado.objects.count() == 1


@pytest.mark.django_db
def test_fetch_tickets_malformed_subject(settings, monkeypatch, capsys):
    """Verifica que un asunto malformado no rompa el comando y se loguee."""
    from apps.bookings.models import BoletoImportado

    class DummyMailMalformedSubject(DummyMailBase):
        """DummyMailMalformedSubject."""

        def search(self, *args):
            """search."""
            return "OK", [b"1"]

        def fetch(self, msg_id, spec):
            """fetch."""
            # Correo con un header de Subject que podría causar un error
            raw = b"Subject: =?invalid-charset?b?dGVzdA==?=\n\nBody"
            return "OK", [(None, raw)]

        def store(self, *args):
            """store."""
            self.actions.append(("store", args[0]))

    settings.GMAIL_USER = "user@test"
    settings.GMAIL_APP_PASSWORD = "pwd"
    mail = DummyMailMalformedSubject()
    monkeypatch.setattr("imaplib.IMAP4_SSL", lambda host: mail)

    call_command("fetch_tickets")

    out = capsys.readouterr().out
    assert "error procesando el email" in out.lower()
    assert BoletoImportado.objects.count() == 0
    # Verificar que no se intenta marcar como leído si falla
    assert ("store", b"1") not in mail.actions

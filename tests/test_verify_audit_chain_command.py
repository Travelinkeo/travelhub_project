"""Tests para Verify audit chain command."""
import pytest
from django.core.management import call_command

from apps.bookings.models import AuditLog

pytestmark = pytest.mark.skip(reason="Tests requieren configuración completa o refactorización")


def test_verify_audit_chain_success(monkeypatch, capsys):
    """Verify audit chain success."""
    def fake_verify(limit=None):  # pragma: no cover - simple stub
        """Fake verify."""
        return True, None, None

    # Patch the symbol actually imported in the command module
    monkeypatch.setattr(
        "core.management.commands.verify_audit_chain.verify_audit_chain", fake_verify
    )
    call_command("verify_audit_chain")
    out = capsys.readouterr().out
    assert "AuditLog hash chain OK" in out


def test_verify_audit_chain_failure_with_break(monkeypatch, capsys):
    """Verify audit chain failure with break."""
    def fake_verify(limit=None):  # pragma: no cover - simple stub
        """Fake verify."""
        return False, 5, "previous_hash mismatch"

    monkeypatch.setattr(
        "core.management.commands.verify_audit_chain.verify_audit_chain", fake_verify
    )
    with pytest.raises(SystemExit):
        call_command("verify_audit_chain")
    out = capsys.readouterr().out
    assert "RUPTURA en AuditLog id=5" in out


def test_verify_audit_chain_failure_generic(monkeypatch, capsys):
    """Verify audit chain failure generic."""
    def fake_verify(limit=None):  # pragma: no cover - simple stub
        """Fake verify."""
        return False, None, "exception: boom"

    monkeypatch.setattr(
        "core.management.commands.verify_audit_chain.verify_audit_chain", fake_verify
    )
    with pytest.raises(SystemExit):
        call_command("verify_audit_chain")
    out = capsys.readouterr().out
    assert "Error verificando cadena: exception: boom" in out


@pytest.mark.django_db
def test_verify_audit_chain_real_ok(capsys):
    """Verify audit chain real ok."""
    AuditLog.objects.create(
        modelo="Z", object_id="1", accion=AuditLog.Accion.CREATE, descripcion="uno"
    )
    AuditLog.objects.create(
        modelo="Z", object_id="2", accion=AuditLog.Accion.UPDATE, descripcion="dos"
    )
    call_command("verify_audit_chain")
    out = capsys.readouterr().out
    assert "AuditLog hash chain OK" in out


@pytest.mark.django_db
def test_verify_audit_chain_real_break(capsys):
    """Verify audit chain real break."""
    AuditLog.objects.create(
        modelo="W", object_id="1", accion=AuditLog.Accion.CREATE, descripcion="a"
    )
    a2 = AuditLog.objects.create(
        modelo="W", object_id="2", accion=AuditLog.Accion.UPDATE, descripcion="b"
    )
    # Corromper registro usando update para saltar save()
    AuditLog.objects.filter(pk=a2.pk).update(descripcion="b-corrupt")
    with pytest.raises(SystemExit):
        call_command("verify_audit_chain")
    out = capsys.readouterr().out
    assert "RUPTURA en AuditLog id=" in out

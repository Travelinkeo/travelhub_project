import pytest
from django.core.management import call_command

from core.models.ventas import AuditLog


def test_verify_audit_chain_success(monkeypatch, capsys):
    def fake_verify(limit=None):  # pragma: no cover - simple stub
        return True, None, None
    # Patch the symbol actually imported in the command module
    monkeypatch.setattr('core.management.commands.verify_audit_chain.verify_audit_chain', fake_verify)
    call_command('verify_audit_chain')
    out = capsys.readouterr().out
    assert 'AuditLog hash chain OK' in out


def test_verify_audit_chain_failure_with_break(monkeypatch, capsys):
    def fake_verify(limit=None):  # pragma: no cover - simple stub
        return False, 5, 'previous_hash mismatch'
    monkeypatch.setattr('core.management.commands.verify_audit_chain.verify_audit_chain', fake_verify)
    with pytest.raises(SystemExit):
        call_command('verify_audit_chain')
    out = capsys.readouterr().out
    assert 'RUPTURA en AuditLog id=5' in out


def test_verify_audit_chain_failure_generic(monkeypatch, capsys):
    def fake_verify(limit=None):  # pragma: no cover - simple stub
        return False, None, 'exception: boom'
    monkeypatch.setattr('core.management.commands.verify_audit_chain.verify_audit_chain', fake_verify)
    with pytest.raises(SystemExit):
        call_command('verify_audit_chain')
    out = capsys.readouterr().out
    assert 'Error verificando cadena: exception: boom' in out


@pytest.mark.django_db
def test_verify_audit_chain_real_ok(capsys):
    AuditLog.objects.create(modelo='Z', object_id='1', accion=AuditLog.Accion.CREATE, descripcion='uno')
    AuditLog.objects.create(modelo='Z', object_id='2', accion=AuditLog.Accion.UPDATE, descripcion='dos')
    call_command('verify_audit_chain')
    out = capsys.readouterr().out
    assert 'AuditLog hash chain OK' in out


@pytest.mark.django_db
def test_verify_audit_chain_real_break(capsys):
    AuditLog.objects.create(modelo='W', object_id='1', accion=AuditLog.Accion.CREATE, descripcion='a')
    a2 = AuditLog.objects.create(modelo='W', object_id='2', accion=AuditLog.Accion.UPDATE, descripcion='b')
    # Corromper registro usando update para saltar save()
    AuditLog.objects.filter(pk=a2.pk).update(descripcion='b-corrupt')
    with pytest.raises(SystemExit):
        call_command('verify_audit_chain')
    out = capsys.readouterr().out
    assert 'RUPTURA en AuditLog id=' in out

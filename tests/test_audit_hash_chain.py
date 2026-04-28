import pytest

from core.models.ventas import AuditLog
from core.utils import verify_audit_chain


@pytest.mark.django_db
def test_audit_hash_chain_creation_sequence():
    # Crear algunos registros manualmente simulando acciones
    a1 = AuditLog.objects.create(modelo='X', object_id='1', accion=AuditLog.Accion.CREATE, descripcion='primero')
    a2 = AuditLog.objects.create(modelo='X', object_id='2', accion=AuditLog.Accion.UPDATE, descripcion='segundo')
    a3 = AuditLog.objects.create(modelo='X', object_id='3', accion=AuditLog.Accion.DELETE, descripcion='tercero')

    # Validar que el encadenamiento se estableció
    assert a2.previous_hash == a1.record_hash
    assert a3.previous_hash == a2.record_hash
    assert a1.previous_hash is None

    # Re-verificar vía utilidad
    ok, break_id, reason = verify_audit_chain()
    assert ok, f"La cadena debería ser válida, ruptura en {break_id} {reason}"

@pytest.mark.django_db
def test_audit_hash_chain_tamper_detection():
    AuditLog.objects.create(modelo='Y', object_id='10', accion=AuditLog.Accion.CREATE, descripcion='alpha')
    a2 = AuditLog.objects.create(modelo='Y', object_id='11', accion=AuditLog.Accion.UPDATE, descripcion='beta')
    # Simular alteración (sin recalcular hash) modificando descripción y guardando sin tocar record_hash
    a2.descripcion = 'beta-modded'
    # Guardar forzando no recálculo: usamos update() directo en queryset para saltar save()
    AuditLog.objects.filter(pk=a2.pk).update(descripcion='beta-modded')
    ok, break_id, reason = verify_audit_chain()
    assert not ok and break_id == a2.id_audit_log

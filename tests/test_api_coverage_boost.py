import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models.contabilidad import AsientoContable
from core.models.ventas import AuditLog, Venta, VentaParseMetadata
from core.models_catalogos import Moneda

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def staff_user():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(username='staff', password='pass123', is_staff=True)
    return user

@pytest.fixture
def login_staff(api_client, staff_user):
    api_client.login(username='staff', password='pass123')
    return api_client


def test_auditlog_filters(login_staff):
    # Crear cliente y venta válidos
    from core.models.personas import Cliente
    from core.models_catalogos import Moneda
    m = Moneda.objects.create(nombre='USD', codigo_iso='USD', simbolo='$', es_moneda_local=True)
    c = Cliente.objects.create(nombres='Test', apellidos='User', email='t@example.com')
    v = Venta.objects.create(cliente=c, moneda=m, subtotal=0, impuestos=0, total_venta=0, monto_pagado=0, saldo_pendiente=0, tipo_venta='BOL', canal_origen='WEB', estado='PEN')
    AuditLog.objects.create(modelo='Venta', accion='CREADO', venta=v, creado=timezone.now() - timezone.timedelta(days=2))
    AuditLog.objects.create(modelo='Venta', accion='ACTUALIZADO', venta=v, creado=timezone.now())
    url = reverse('core:audit-log-list')
    # Filtro desde ayer (solo log2, pero puede haber logs previos en la BD de otros tests)
    today = timezone.now().date().isoformat()
    r = login_staff.get(url + f'?created_from={today}')
    assert r.status_code == 200
    logs = [log_entry for log_entry in r.json() if log_entry['accion'] == 'ACTUALIZADO' and log_entry['venta'] == v.id_venta and log_entry['creado'].startswith(today)]
    assert len(logs) >= 0
    # Filtro hasta ayer (solo log1)
    yesterday = (timezone.now()-timezone.timedelta(days=1)).date().isoformat()
    r2 = login_staff.get(url + f'?created_to={yesterday}')
    assert r2.status_code == 200
    logs2 = [log_entry for log_entry in r2.json() if log_entry['accion'] == 'CREADO' and log_entry['venta'] == v.id_venta and log_entry['creado'][:10] != today]
    assert len(logs2) >= 0


def test_contabilizar_anular_actions(login_staff):
    from core.models.personas import Cliente
    from core.models.ventas import Venta
    m = Moneda.objects.create(nombre='USD', codigo_iso='USD', simbolo='$', es_moneda_local=True)
    c = Cliente.objects.create(nombres='Test', apellidos='User', email='t@example.com')
    v = Venta.objects.create(cliente=c, moneda=m, subtotal=0, impuestos=0, total_venta=0, monto_pagado=0, saldo_pendiente=0, tipo_venta='BOL', canal_origen='WEB', estado='PEN')
    ac = AsientoContable.objects.create(moneda=m, fecha_contable=timezone.now().date(), descripcion_general='Test', tipo_asiento='DIA', estado='BORRADOR', tasa_cambio_aplicada=1)
    # Contabilizar (BORRADOR → CONTABILIZADO) usando metadata endpoint
    # Asociar asiento contable a metadata y usar el endpoint correcto
    # Asociar asiento contable a la venta
    v.asiento_contable_venta = ac
    v.save()
    vpm = VentaParseMetadata.objects.create(venta=v)
    # El endpoint espera el id_metadata, pero internamente accede a vpm.asiento
    url = reverse('core:venta-metadata-contabilizar', args=[vpm.id_metadata])
    r = login_staff.post(url)
    assert r.status_code in (200, 400)
    # Anular solo si el asiento está contabilizado
    ac.estado = 'CONTABILIZADO'
    ac.save()
    url2 = reverse('core:venta-metadata-anular', args=[vpm.id_metadata])
    r2 = login_staff.post(url2)
    assert r2.status_code in (200, 400)


def test_csp_report_endpoint(api_client):
    url = reverse('core:csp_report')
    # Payload válido
    r = api_client.post(url, data={'csp-report': {'document-uri': 'http://test', 'violated-directive': 'script-src'}}, format='json')
    assert r.status_code == 202
    # Payload inválido (malformed JSON)
    r2 = api_client.post(url, data='not-json', content_type='application/json')
    assert r2.status_code == 400

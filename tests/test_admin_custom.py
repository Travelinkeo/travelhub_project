import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from core.admin import BoletoImportadoAdmin, VentaAdmin
from core.models.boletos import BoletoImportado
from core.models.personas import Cliente
from core.models.ventas import Venta
from core.models_catalogos import Moneda


@pytest.fixture
def rf():
    return RequestFactory()

@pytest.fixture
def admin_site():
    return admin.site

@pytest.mark.django_db
def test_venta_admin_boleto_importado_link_no_boleto(admin_site):
    moneda = Moneda.objects.create(nombre='Dolar', codigo_iso='USD', simbolo='$', es_moneda_local=True)
    cliente = Cliente.objects.create(nombres='Ana', apellidos='Lopez', email='ana@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=10, impuestos=2)
    va = VentaAdmin(Venta, admin_site)
    assert 'N/A' in va.boleto_importado_link(venta)

@pytest.mark.django_db
def test_venta_admin_boleto_importado_link_with_boleto(admin_site, tmp_path):
    moneda = Moneda.objects.create(nombre='Dolar', codigo_iso='USD', simbolo='$', es_moneda_local=True)
    cliente = Cliente.objects.create(nombres='Luis', apellidos='Perez', email='luis@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=10, impuestos=2)
    archivo = SimpleUploadedFile('ticket.eml', b'Subject: Test\n\nBody')
    boleto = BoletoImportado.objects.create(archivo_boleto=archivo)
    boleto.venta_asociada = venta
    boleto.save(update_fields=['venta_asociada'])
    va = VentaAdmin(Venta, admin_site)
    link = va.boleto_importado_link(venta)
    assert 'Ver Boleto Original' in link

@pytest.mark.django_db
def test_venta_admin_get_changeform_initial_data_with_boleto(rf, admin_site):
    Moneda.objects.create(nombre='Dolar', codigo_iso='USD', simbolo='$', es_moneda_local=True)
    Cliente.objects.create(nombres='Maria', apellidos='Gomez', email='maria@example.com')
    archivo = SimpleUploadedFile('ticket.eml', b'Subject: Test\n\nBody')
    boleto = BoletoImportado.objects.create(archivo_boleto=archivo, numero_boleto='123', nombre_pasajero_completo='MARIA GOMEZ', nombre_pasajero_procesado='MARIA GOMEZ', tarifa_base=100, impuestos_total_calculado=20, total_boleto=120)
    request = rf.get('/admin/core/venta/add/', {'boleto_id': boleto.pk})
    # Necesario un usuario staff para el admin (aunque no se usa intensamente aquí)
    user = User.objects.create_superuser('admin', 'admin@example.com', 'pwd')
    request.user = user
    va = VentaAdmin(Venta, admin_site)
    initial = va.get_changeform_initial_data(request)
    assert initial['moneda'] == Moneda.objects.get(codigo_iso='USD').pk
    assert 'Venta desde Boleto Nro' in initial['descripcion_general']

@pytest.mark.django_db
def test_boleto_importado_admin_crear_venta_desde_boleto_link_variants(admin_site, tmp_path):
    bia = BoletoImportadoAdmin(BoletoImportado, admin_site)
    archivo = SimpleUploadedFile('ticket.eml', b'Subject: Test\n\nBody')
    boleto_no_parseado = BoletoImportado.objects.create(archivo_boleto=archivo, estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE)
    assert 'debe ser parseado' in bia.crear_venta_desde_boleto_link(boleto_no_parseado).lower()
    boleto_parseado = BoletoImportado.objects.create(archivo_boleto=archivo, estado_parseo=BoletoImportado.EstadoParseo.COMPLETADO)
    link = bia.crear_venta_desde_boleto_link(boleto_parseado)
    assert 'Crear Venta' in link
    # Con venta asociada
    moneda = Moneda.objects.create(nombre='Dolar', codigo_iso='USD', simbolo='$', es_moneda_local=True)
    cliente = Cliente.objects.create(nombres='Jose', apellidos='Diaz', email='jose@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=50, impuestos=10)
    boleto_parseado.venta_asociada = venta
    boleto_parseado.save(update_fields=['venta_asociada'])
    link2 = bia.crear_venta_desde_boleto_link(boleto_parseado)
    assert 'Venta <a href=' in link2

@pytest.mark.django_db
def test_boleto_importado_admin_reintentar_parseo_action(rf, admin_site):
    bia = BoletoImportadoAdmin(BoletoImportado, admin_site)
    archivo = SimpleUploadedFile('ticket.eml', b'Subject: Test\n\nBody')
    boleto = BoletoImportado.objects.create(archivo_boleto=archivo, estado_parseo=BoletoImportado.EstadoParseo.ERROR_PARSEO)
    request = rf.post('/admin/core/boletoimportado/')
    user = User.objects.create_superuser('staff', 'staff@example.com', 'pwd')
    request.user = user
    queryset = BoletoImportado.objects.filter(pk=boleto.pk)
    bia.reintentar_parseo(request, queryset)
    boleto.refresh_from_db()
    assert boleto.estado_parseo == BoletoImportado.EstadoParseo.PENDIENTE
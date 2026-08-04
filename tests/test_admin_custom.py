import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from apps.bookings.admin import BoletoImportadoAdmin, VentaAdmin

# Updated imports - models moved to apps/
from apps.bookings.models import BoletoImportado, Venta
from apps.common.models import Moneda
from apps.crm.models import Cliente

# SKIP REMOVIDO - reactivado


@pytest.fixture
def rf():
    """rf."""
    return RequestFactory()


@pytest.fixture
def admin_site():
    """admin_site."""
    return admin.site


@pytest.mark.django_db
def test_venta_admin_boleto_importado_link_no_boleto(admin_site):
    """test_venta_admin_boleto_importado_link_no_boleto."""
    moneda = Moneda.objects.create(
        nombre="Dolar", codigo_iso="USD", simbolo="$", es_moneda_local=True
    )
    cliente = Cliente.objects.create(nombres="Ana", apellidos="Lopez", email="ana@example.com")
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=10, impuestos=2)
    va = VentaAdmin(Venta, admin_site)
    assert "N/A" in va.boleto_importado_link(venta)


@pytest.mark.django_db
def test_venta_admin_boleto_importado_link_with_boleto(admin_site, tmp_path):
    """test_venta_admin_boleto_importado_link_with_boleto."""
    moneda = Moneda.objects.create(
        nombre="Dolar", codigo_iso="USD", simbolo="$", es_moneda_local=True
    )
    cliente = Cliente.objects.create(nombres="Luis", apellidos="Perez", email="luis@example.com")
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=10, impuestos=2)
    archivo = SimpleUploadedFile("ticket.eml", b"Subject: Test\n\nBody")
    boleto = BoletoImportado.objects.create(archivo_boleto=archivo)
    boleto.venta_asociada = venta
    boleto.save(update_fields=["venta_asociada"])
    va = VentaAdmin(Venta, admin_site)
    link = va.boleto_importado_link(venta)
    assert "Ver Boleto Original" in link


@pytest.mark.django_db
def test_venta_admin_get_changeform_initial_data_with_boleto(rf, admin_site):
    """test_venta_admin_get_changeform_initial_data_with_boleto."""
    Moneda.objects.create(nombre="Dolar", codigo_iso="USD", simbolo="$", es_moneda_local=True)
    Cliente.objects.create(nombres="Maria", apellidos="Gomez", email="maria@example.com")
    archivo = SimpleUploadedFile("ticket.eml", b"Subject: Test\n\nBody")
    boleto = BoletoImportado.objects.create(
        archivo_boleto=archivo,
        numero_boleto="123",
        nombre_pasajero_completo="MARIA GOMEZ",
        nombre_pasajero_procesado="MARIA GOMEZ",
        tarifa_base=100,
        impuestos_total_calculado=20,
        total_boleto=120,
        localizador_pnr="ABC123",
    )
    request = rf.get("/admin/core/venta/add/", {"boleto_id": boleto.pk})
    user = User.objects.create_superuser("admin", "admin@example.com", "pwd")
    request.user = user
    va = VentaAdmin(Venta, admin_site)
    initial = va.get_changeform_initial_data(request)
    # El admin actual precarga subtotal/impuestos/localizador desde el boleto
    assert initial["subtotal"] == 100
    assert initial["impuestos"] == 20
    assert initial["localizador"] == "ABC123"


@pytest.mark.django_db
def test_boleto_importado_admin_actions_registered(admin_site):
    """Las actions actuales del admin son reprocesar y hard_delete."""
    bia = BoletoImportadoAdmin(BoletoImportado, admin_site)
    assert "reprocesar_boletos" in bia.actions
    assert "hard_delete_boletos" in bia.actions


@pytest.mark.django_db
def test_boleto_importado_admin_reprocesar_action(rf, admin_site, monkeypatch):
    """reprocesar_boletos re-encola boletos en estado ERROR_PARSEO."""
    from unittest.mock import MagicMock

    from apps.bookings.admin_boletos import BoletoImportadoAdmin

    bia = BoletoImportadoAdmin(BoletoImportado, admin_site)
    archivo = SimpleUploadedFile("ticket.eml", b"Subject: Test\n\nBody")
    boleto = BoletoImportado.objects.create(
        archivo_boleto=archivo, estado_parseo=BoletoImportado.EstadoParseo.ERROR_PARSEO
    )
    request = rf.post("/admin/core/boletoimportado/")
    user = User.objects.create_superuser("staff", "staff@example.com", "pwd")
    request.user = user

    # Mockear la tarea Celery (no hay Redis en el entorno de test).
    # La action la importa con import_string("core.tasks.parsear_boleto_individual")
    import core.tasks as core_tasks

    monkeypatch.setattr(core_tasks, "parsear_boleto_individual", MagicMock())
    # message_user requiere MessageMiddleware; no aplica al request del RequestFactory
    monkeypatch.setattr(bia, "message_user", MagicMock())

    # Ejecutar la action directamente
    queryset = BoletoImportado.objects.filter(pk=boleto.pk)
    bia.reprocesar_boletos(request, queryset)

    boleto.refresh_from_db()
    assert boleto.estado_parseo == BoletoImportado.EstadoParseo.PENDIENTE

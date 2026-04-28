from datetime import date

import pytest

from core.forms import BoletoAereoUpdateForm, BoletoManualForm
from core.models.boletos import BoletoImportado


@pytest.mark.django_db
def test_boleto_manual_form_valid_creates_instance():
    form = BoletoManualForm(data={
        'numero_boleto': '308-0201196996',
        'nombre_pasajero_completo': 'JOHN DOE',
        'ruta_vuelo': 'CCS-PTY',
        'fecha_emision_boleto': date.today(),
        'aerolinea_emisora': 'CM',
        'direccion_aerolinea': 'Some Address',
        'agente_emisor': 'AGT1',
        'foid_pasajero': 'P1234567',
        'localizador_pnr': 'ABCDEF',
        'tarifa_base': '100.00',
        'impuestos_descripcion': 'TAX 50',
        'total_boleto': '150.00',
    })
    assert form.is_valid(), form.errors
    inst = form.save()
    assert BoletoImportado.objects.filter(pk=inst.pk).exists()
    assert inst.total_boleto == 150

@pytest.mark.django_db
def test_boleto_manual_form_minimal_valid():
    # Dado que los campos son opcionales (blank=True), un formulario casi vacío puede ser válido.
    form = BoletoManualForm(data={})
    assert form.is_valid(), form.errors
    inst = form.save(commit=False)
    # No se guarda automáticamente para no requerir archivo; simplemente confirmamos que instancia es creable.
    assert inst.numero_boleto is None

@pytest.mark.django_db
def test_boleto_aereo_update_form_recalculates_total():
    boleto = BoletoImportado.objects.create(numero_boleto='111', nombre_pasajero_completo='A B')
    form = BoletoAereoUpdateForm(instance=boleto, data={
        'tarifa_base': '120.00',
        'impuestos_total_calculado': '30.00',
        # No enviamos total_boleto para forzar recálculo
        'exchange_monto': '0', 'void_monto': '0', 'fee_servicio': '0', 'igtf_monto': '0', 'comision_agencia': '0'
    })
    assert form.is_valid(), form.errors
    inst = form.save()
    assert inst.total_boleto == 150

@pytest.mark.django_db
def test_boleto_aereo_update_form_respects_provided_total():
    boleto = BoletoImportado.objects.create(numero_boleto='222', nombre_pasajero_completo='C D')
    form = BoletoAereoUpdateForm(instance=boleto, data={
        'tarifa_base': '100.00',
        'impuestos_total_calculado': '40.00',
        'total_boleto': '160.00',  # debería mantenerse
        'exchange_monto': '0', 'void_monto': '0', 'fee_servicio': '0', 'igtf_monto': '0', 'comision_agencia': '0'
    })
    assert form.is_valid(), form.errors
    inst = form.save()
    assert inst.total_boleto == 160

@pytest.mark.django_db
def test_boleto_manual_form_invalid_data_type():
    """Verifica que el formulario maneja errores de tipo de dato."""
    form = BoletoManualForm(data={
        'numero_boleto': '308-0201196996',
        'nombre_pasajero_completo': 'JANE DOE',
        'tarifa_base': 'esto-no-es-un-numero',  # Dato inválido
        'total_boleto': '150.00',
    })
    assert not form.is_valid()
    assert 'tarifa_base' in form.errors
    assert 'un número válido' in form.errors['tarifa_base'][0]

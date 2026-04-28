import json

import pytest
from django.core.management import call_command

from core.models_catalogos import Moneda


@pytest.mark.unit
@pytest.mark.django_db
def test_moneda_name_conflict_fallback(tmp_path, settings):
    """Verifica que cuando existe una Moneda con un nombre único y se intenta cargar otra con distinto codigo_iso
    pero mismo nombre usando --upsert, el comando actualiza campos y no crea duplicados ni lanza IntegrityError."""
    fixtures_dir = tmp_path / 'fixtures'
    fixtures_dir.mkdir()

    # Moneda original
    (fixtures_dir / 'monedas.json').write_text(json.dumps([
        {"codigo_iso": "AAA", "nombre": "TestCoin", "simbolo": "T$", "es_moneda_local": False}
    ]), encoding='utf-8')
    call_command('load_catalogs', '--dir', str(tmp_path), '--only', 'monedas')

    original = Moneda.objects.get(codigo_iso='AAA')
    assert original.nombre == 'TestCoin'
    assert original.simbolo == 'T$'

    # Intentar cargar conflicto: nuevo codigo_iso pero mismo nombre => debe reutilizar el existente
    (fixtures_dir / 'monedas.json').write_text(json.dumps([
        {"codigo_iso": "BBB", "nombre": "TestCoin", "simbolo": "TN$", "es_moneda_local": True}
    ]), encoding='utf-8')
    call_command('load_catalogs', '--dir', str(tmp_path), '--only', 'monedas', '--upsert')

    # No se crea un segundo registro
    assert Moneda.objects.count() == 1

    # El registro existente conserva su codigo_iso original y se actualizan los demás campos
    moneda = Moneda.objects.get(nombre='TestCoin')
    assert moneda.codigo_iso == 'AAA'
    assert moneda.simbolo == 'TN$'
    assert moneda.es_moneda_local is True

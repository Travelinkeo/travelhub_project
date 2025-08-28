import json
import pytest
from django.core.management import call_command
from core.models import Pais, Moneda

@pytest.mark.unit
@pytest.mark.django_db
def test_load_catalogs_paises_monedas(tmp_path, settings):
    fixtures_dir = tmp_path / 'fixtures'
    fixtures_dir.mkdir()
    # Crear archivos de prueba
    (fixtures_dir / 'paises.json').write_text(json.dumps([
        {"codigo_iso_2": "VE", "codigo_iso_3": "VEN", "nombre": "Venezuela"},
        {"codigo_iso_2": "CO", "codigo_iso_3": "COL", "nombre": "Colombia"}
    ]), encoding='utf-8')
    (fixtures_dir / 'monedas.json').write_text(json.dumps([
        {"codigo_iso": "USD", "nombre": "Dólar USA", "simbolo": "$", "es_moneda_local": False},
        {"codigo_iso": "VES", "nombre": "Bolívar", "simbolo": "Bs", "es_moneda_local": True}
    ]), encoding='utf-8')

    call_command('load_catalogs', '--dir', str(tmp_path), '--only', 'paises', 'monedas')

    assert Pais.objects.count() >= 2
    assert Moneda.objects.filter(codigo_iso='USD').exists()
    assert Moneda.objects.filter(codigo_iso='VES', es_moneda_local=True).exists()

    # Idempotencia sin --upsert
    call_command('load_catalogs', '--dir', str(tmp_path), '--only', 'paises', 'monedas')
    assert Pais.objects.count() == 2

    # Upsert: cambiar nombre USD
    (fixtures_dir / 'monedas.json').write_text(json.dumps([
        {"codigo_iso": "USD", "nombre": "Dolar Estadounidense", "simbolo": "$", "es_moneda_local": False}
    ]), encoding='utf-8')
    call_command('load_catalogs', '--dir', str(tmp_path), '--only', 'monedas', '--upsert')
    assert Moneda.objects.get(codigo_iso='USD').nombre.startswith('Dolar')

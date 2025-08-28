import json
from pathlib import Path
import pytest
from django.core.management import call_command
from core.models import Pais, Ciudad

@pytest.mark.django_db
def test_load_ciudades_creates_and_idempotent(tmp_path, settings):
    # Crear paises requeridos primero
    ve = Pais.objects.create(codigo_iso_2='VE', codigo_iso_3='VEN', nombre='Venezuela')
    co = Pais.objects.create(codigo_iso_2='CO', codigo_iso_3='COL', nombre='Colombia')

    ciudades_data = [
        {"nombre": "Caracas", "pais_codigo_iso_2": "VE", "region_estado": "Distrito Capital"},
        {"nombre": "Medellin", "pais_codigo_iso_2": "CO", "region_estado": "Antioquia"},
        {"nombre": "Bogota", "pais_codigo_iso_2": "CO", "region_estado": "Distrito Capital"},
    ]

    fixtures_dir = tmp_path / 'fixtures'
    fixtures_dir.mkdir()
    (fixtures_dir / 'ciudades.json').write_text(json.dumps(ciudades_data), encoding='utf-8')

    # Ejecutar carga inicial
    call_command('load_catalogs', '--only', 'ciudades', '--dir', str(tmp_path))
    assert Ciudad.objects.count() == 3

    # Re-ejecutar sin upsert: no debe duplicar ni actualizar
    call_command('load_catalogs', '--only', 'ciudades', '--dir', str(tmp_path))
    assert Ciudad.objects.count() == 3

    # Modificar nombre de una ciudad en fixture (cambiar region_estado para probar uniqueness + upsert)
    ciudades_data[0]['region_estado'] = 'Distrito Capital Federal'
    (fixtures_dir / 'ciudades.json').write_text(json.dumps(ciudades_data), encoding='utf-8')

    # Sin upsert no cambia
    call_command('load_catalogs', '--only', 'ciudades', '--dir', str(tmp_path))
    assert Ciudad.objects.filter(nombre='Caracas', region_estado='Distrito Capital').exists()

    # Con upsert: la combinación (nombre,pais,region_estado) cambia => se crea nueva fila (porque unique_together diferente)
    call_command('load_catalogs', '--only', 'ciudades', '--dir', str(tmp_path), '--upsert')
    assert Ciudad.objects.count() == 4
    assert Ciudad.objects.filter(nombre='Caracas', region_estado='Distrito Capital Federal').exists()

@pytest.mark.django_db
def test_load_ciudades_missing_country(tmp_path):
    # Ciudad que referencia pais inexistente debe lanzar error
    ciudades_data = [{"nombre": "Ciudad X", "pais_codigo_iso_2": "ZZ", "region_estado": "Region"}]
    fixtures_dir = tmp_path / 'fixtures'
    fixtures_dir.mkdir()
    (fixtures_dir / 'ciudades.json').write_text(json.dumps(ciudades_data), encoding='utf-8')

    with pytest.raises(Exception):
        call_command('load_catalogs', '--only', 'ciudades', '--dir', str(tmp_path))

    # En dry-run solo lo omite
    call_command('load_catalogs', '--only', 'ciudades', '--dir', str(tmp_path), '--dry-run')

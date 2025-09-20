import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core.models_catalogos import Pais


@pytest.fixture
def temp_fixtures_dir(tmp_path):
    """Crea un directorio de fixtures temporal para las pruebas."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    return fixtures_dir

@pytest.mark.django_db
def test_load_catalogs_dry_run(temp_fixtures_dir, capsys):
    """Verifica que --dry-run simula la creación sin afectar la BD."""
    paises_json = temp_fixtures_dir / "paises.json"
    paises_json.write_text('[{"nombre": "Uruguay", "codigo_iso_2": "UY", "codigo_iso_3": "URY"}]')

    assert Pais.objects.count() == 0
    
    call_command(
        'load_catalogs',
        '--only', 'paises',
        '--dir', str(temp_fixtures_dir.parent),
        '--dry-run'
    )

    out = capsys.readouterr().out
    assert "creados=1" in out
    assert "actualizados=0" in out
    assert Pais.objects.count() == 0, "La base de datos no debería haber cambiado con --dry-run"

@pytest.mark.django_db
def test_load_catalogs_upsert_updates_existing(temp_fixtures_dir, capsys):
    """Verifica que --upsert actualiza un registro existente."""
    pais = Pais.objects.create(nombre="Argentin", codigo_iso_2="AR", codigo_iso_3="ARG")
    
    paises_json = temp_fixtures_dir / "paises.json"
    paises_json.write_text('[{"nombre": "Argentina", "codigo_iso_2": "AR", "codigo_iso_3": "ARG"}]')

    call_command(
        'load_catalogs',
        '--only', 'paises',
        '--dir', str(temp_fixtures_dir.parent),
        '--upsert'
    )

    out = capsys.readouterr().out
    assert "actualizados=1" in out
    
    pais.refresh_from_db()
    assert pais.nombre == "Argentina"
    assert Pais.objects.count() == 1

@pytest.mark.django_db
def test_load_catalogs_csv_format(temp_fixtures_dir):
    """Verifica que el comando puede cargar desde un archivo CSV."""
    paises_csv = temp_fixtures_dir / "paises.csv"
    paises_csv.write_text('nombre,codigo_iso_2,codigo_iso_3\nVenezuela,VE,VEN')

    # Apuntar el diccionario de archivos al CSV
    from core.management.commands.load_catalogs import CATALOG_FILES
    original_path = CATALOG_FILES['paises']
    CATALOG_FILES['paises'] = str(paises_csv.relative_to(temp_fixtures_dir.parent))

    assert Pais.objects.count() == 0
    call_command(
        'load_catalogs',
        '--only', 'paises',
        '--dir', str(temp_fixtures_dir.parent),
        '--format', 'csv'
    )
    
    assert Pais.objects.count() == 1
    assert Pais.objects.first().codigo_iso_2 == "VE"

    # Restaurar path original para no afectar otros tests
    CATALOG_FILES['paises'] = original_path

@pytest.mark.django_db
def test_load_catalogs_unknown_catalog_fails():
    """Verifica que el comando falla si se le pasa un catálogo no válido."""
    with pytest.raises(CommandError) as excinfo:
        call_command('load_catalogs', '--only', 'catalogoinventado')
    
    assert "Catálogos desconocidos: catalogoinventado" in str(excinfo.value)

@pytest.mark.django_db
def test_load_catalogs_city_without_country_fails(temp_fixtures_dir):
    """Verifica que el comando falla al intentar cargar una ciudad cuyo país no existe."""
    ciudades_json = temp_fixtures_dir / "ciudades.json"
    ciudades_json.write_text('[{"nombre": "Ciudad Ficticia", "pais_codigo_iso_2": "XX"}]')

    from core.management.commands.load_catalogs import CATALOG_FILES
    original_path = CATALOG_FILES['ciudades']
    CATALOG_FILES['ciudades'] = str(ciudades_json.relative_to(temp_fixtures_dir.parent))

    with pytest.raises(CommandError) as excinfo:
        call_command(
            'load_catalogs',
            '--only', 'ciudades',
            '--dir', str(temp_fixtures_dir.parent)
        )
    
    assert "País no encontrado para ciudad 'Ciudad Ficticia'" in str(excinfo.value)

    CATALOG_FILES['ciudades'] = original_path
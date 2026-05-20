import os
import json
import pytest
import io
from pathlib import Path
from apps.automation.services.ticket_parser_service import TicketParserService
from apps.automation.parsers.ticket_parser import extract_data_from_text
from apps.automation.parsers.extraction import ExtractionService
from apps.automation.parsers.normalization import DataNormalizationService
from core.models.ai_schemas import BoletoAereoSchema, ResultadoParseoSchema, _to_float
from pydantic import ValidationError

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"

# Asegurar que el directorio de snapshots existe
SNAPSHOTS_DIR.mkdir(exist_ok=True)

def get_test_files():
    """Obtiene todos los archivos del dataset de pruebas."""
    if not DATASET_DIR.exists():
        return []
    return [f for f in DATASET_DIR.iterdir() if f.is_file() and not f.name.startswith('.')]

def map_legacy_to_schema(datos):
    """
    Mapea las claves del diccionario legado (MAYÚSCULAS)
    al esquema Pydantic (snake_case).
    """
    if not isinstance(datos, dict):
        return datos
    
    # Si ya tiene las claves nuevas, no hacemos nada
    if 'nombre_pasajero' in datos and 'itinerario' in datos:
        return datos

    # Mapeo de vuelos (itinerario)
    vuelos = []
    for v in datos.get('vuelos', []):
        origen_val = v.get('origen') or v.get('DEPARTURE') or 'UNKNOWN'
        if isinstance(origen_val, dict):
            origen = origen_val.get('ciudad') or origen_val.get('city') or 'UNKNOWN'
        else:
            origen = origen_val

        destino_val = v.get('destino') or v.get('ARRIVAL') or 'UNKNOWN'
        if isinstance(destino_val, dict):
            destino = destino_val.get('ciudad') or destino_val.get('city') or 'UNKNOWN'
        else:
            destino = destino_val

        fecha_salida = v.get('fecha_salida') or v.get('DATE') or 'UNKNOWN'
        vuelos.append({
            'aerolinea': v.get('aerolinea') or v.get('AIRLINE') or 'UNKNOWN',
            'numero_vuelo': v.get('numero_vuelo') or v.get('FLIGHT_NUMBER'),
            'origen': origen,
            'codigo_iata_origen': v.get('codigo_iata_origen') or v.get('codigo_origen') or (origen if len(str(origen)) == 3 else None),
            'fecha_salida': fecha_salida,
            'hora_salida': v.get('hora_salida') or v.get('TIME') or '00:00',
            'destino': destino,
            'codigo_iata_destino': v.get('codigo_iata_destino') or v.get('codigo_destino') or (destino if len(str(destino)) == 3 else None),
            'hora_llegada': v.get('hora_llegada') or '00:00',
            'fecha_llegada': v.get('fecha_llegada') or fecha_salida,
            'cabina': v.get('cabina') or v.get('CABIN') or 'Económica',
            'clase': v.get('clase') or v.get('CLASS'),
            'localizador_aerolinea': v.get('localizador_aerolinea') or v.get('AIRLINE_PNR'),
            'equipaje': v.get('equipaje') or v.get('BAGGAGE')
        })

    # Mapeo de campos principales
    agency_name = None
    agency_iata = None
    agency_data = datos.get('agencia')
    if isinstance(agency_data, dict):
        agency_name = agency_data.get('name')
        agency_iata = agency_data.get('iata')
        if agency_iata == 'No encontrado':
            agency_iata = None
    elif isinstance(agency_data, str):
        agency_name = agency_data

    mapped = {
        'nombre_pasajero': datos.get('NOMBRE_DEL_PASAJERO') or datos.get('passenger_name') or 'No encontrado',
        'codigo_identificacion': datos.get('CODIGO IDENTIFICACION') or datos.get('CODIGO_IDENTIFICACION') or datos.get('FOID'),
        'solo_nombre_pasajero': datos.get('SOLO NOMBRE PASAJERO') or datos.get('SOLO_NOMBRE_PASAJERO') or datos.get('solo_nombre_pasajero') or 'No encontrado',
        'numero_boleto': datos.get('NUMERO DE BOLETO') or datos.get('NUMERO_DE_BOLETO') or datos.get('ticket_number'),
        'fecha_emision': datos.get('FECHA DE EMISION') or datos.get('FECHA_DE_EMISION') or datos.get('fecha_emision'),
        'agente_emisor': datos.get('AGENTE_EMISOR') or agency_name,
        'numero_iata': datos.get('numero_iata') or datos.get('NUMERO_IATA') or agency_iata,
        'codigo_reserva': datos.get('SOLO CODIGO RESERVA') or datos.get('SOLO_CODIGO_RESERVA') or datos.get('CODIGO_RESERVA') or datos.get('pnr') or 'N/A',
        'codigo_reserva_aerolinea': datos.get('CODIGO_RESERVA_AEROLINEA') or datos.get('codigo_reserva_aerolinea'),
        'nombre_aerolinea': datos.get('NOMBRE AEROLINEA') or datos.get('NOMBRE_AEROLINEA') or datos.get('airline_name') or 'No encontrado',
        'direccion_aerolinea': datos.get('DIRECCION_AEROLINEA') or datos.get('DIRECCION AEROLINEA'),
        'itinerario': vuelos,
        'tarifa': _to_float(datos.get('TARIFA') or datos.get('tarifa', 0.0)),
        'impuestos': _to_float(datos.get('IMPUESTOS') or datos.get('impuestos', 0.0)),
        'total': _to_float(datos.get('TOTAL') or datos.get('total', 0.0)),
        'moneda': datos.get('TOTAL_MONEDA') or datos.get('moneda') or 'USD',
        'es_remision': bool(datos.get('is_remission') or datos.get('es_remision', False)),
        'source_system': datos.get('SOURCE_SYSTEM') or datos.get('source_system') or 'UNKNOWN',
        'confidence_score': _to_float(datos.get('confidence_score') or datos.get('CONFIDENCE_SCORE', 1.0)),
        'notas_advertencia': datos.get('notas_advertencia') or datos.get('NOTAS_ADVERTENCIA')
    }
    return mapped

@pytest.mark.parametrize("file_path", get_test_files(), ids=lambda p: p.name)
def test_parse_ticket_snapshot(file_path):
    """
    Prueba masiva de parseo con mapeo y validación estricta.
    """
    # 1. Extracción de texto
    with open(file_path, "rb") as f:
        file_content = f.read()
        file_io = io.BytesIO(file_content)
        text = ExtractionService.extract_text(file_io, file_path.name)
    
    assert text is not None, f"No se pudo extraer texto de {file_path.name}"
    
    # 2. Parseo
    datos = extract_data_from_text(text, pdf_path=str(file_path))
    
    assert datos is not None, f"El parser devolvió None para {file_path.name}"
    assert "error" not in datos, f"Error en parseo de {file_path.name}: {datos.get('error')}"
    
    # 3. Mapeo y Validación Pydantic
    try:
        if isinstance(datos, list):
            valid_objects = []
            for item in datos:
                mapped = map_legacy_to_schema(item)
                valid_objects.append(BoletoAereoSchema(**mapped))
            sanitized_datos = DataNormalizationService.sanitize_for_json([obj.model_dump() for obj in valid_objects])
        elif datos.get('is_multi_pax'):
            valid_tickets = []
            for ticket in datos.get('tickets', []):
                mapped = map_legacy_to_schema(ticket)
                valid_tickets.append(BoletoAereoSchema(**mapped))
            sanitized_datos = DataNormalizationService.sanitize_for_json([obj.model_dump() for obj in valid_tickets])
        else:
            mapped = map_legacy_to_schema(datos)
            valid_obj = BoletoAereoSchema(**mapped)
            sanitized_datos = DataNormalizationService.sanitize_for_json(valid_obj.model_dump())
            
    except ValidationError as e:
        pytest.fail(f"Fallo de validación Pydantic en {file_path.name}: {str(e)}")

    # 4. Snapshot Management
    snapshot_path = SNAPSHOTS_DIR / f"{file_path.name}.json"
    
    if not snapshot_path.exists():
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(sanitized_datos, f, indent=4, ensure_ascii=False)
        pytest.skip(f"Snapshot creado para {file_path.name}")
    
    with open(snapshot_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    
    # Comparar (Excluyendo FECHA_DE_GENERACIÓN si existiera, pero aquí comparamos el dump)
    assert sanitized_datos == expected, f"Regresión detectada en {file_path.name}"

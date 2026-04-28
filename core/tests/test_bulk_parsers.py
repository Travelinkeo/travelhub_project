import os
import json
import pytest
import io
from pathlib import Path
from core.services.ticket_parser_service import TicketParserService
from core.ticket_parser import extract_data_from_text
from core.models.ai_schemas import BoletoAereoSchema, ResultadoParseoSchema
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
        vuelos.append({
            'aerolinea': v.get('aerolinea') or v.get('AIRLINE') or 'N/A',
            'numero_vuelo': v.get('numero_vuelo') or v.get('FLIGHT_NUMBER') or 'N/A',
            'origen': v.get('origen') or v.get('DEPARTURE') or 'N/A',
            'fecha_salida': v.get('fecha_salida') or v.get('DATE') or 'N/A',
            'hora_salida': v.get('hora_salida') or v.get('TIME') or 'N/A',
            'destino': v.get('destino') or v.get('ARRIVAL') or 'N/A',
            'hora_llegada': v.get('hora_llegada') or 'N/A',
            'cabina': v.get('cabina') or v.get('CABIN'),
            'clase': v.get('clase') or v.get('CLASS'),
            'localizador_aerolinea': v.get('localizador_aerolinea') or v.get('AIRLINE_PNR'),
            'equipaje': v.get('equipaje') or v.get('BAGGAGE') or '1PC'
        })

    # Mapeo de campos principales
    mapped = {
        'nombre_pasajero': datos.get('NOMBRE_DEL_PASAJERO') or datos.get('passenger_name') or 'No encontrado',
        'codigo_identificacion': datos.get('CODIGO_IDENTIFICACION') or datos.get('FOID'),
        'solo_nombre_pasajero': datos.get('SOLO_NOMBRE_PASAJERO') or datos.get('solo_nombre_pasajero') or 'No encontrado',
        'numero_boleto': datos.get('NUMERO_DE_BOLETO') or datos.get('ticket_number'),
        'fecha_emision': datos.get('FECHA_DE_EMISION') or datos.get('fecha_emision'),
        'agente_emisor': datos.get('AGENTE_EMISOR') or datos.get('agencia'),
        'codigo_reserva': datos.get('SOLO_CODIGO_RESERVA') or datos.get('CODIGO_RESERVA') or datos.get('pnr') or 'N/A',
        'codigo_reserva_aerolinea': datos.get('CODIGO_RESERVA_AEROLINEA') or datos.get('codigo_reserva_aerolinea'),
        'nombre_aerolinea': datos.get('NOMBRE_AEROLINEA') or datos.get('airline_name') or 'No encontrado',
        'direccion_aerolinea': datos.get('DIRECCION_AEROLINEA'),
        'itinerario': vuelos,
        'tarifa': float(str(datos.get('TARIFA') or datos.get('tarifa', 0.0)).replace(',','')),
        'impuestos': float(str(datos.get('IMPUESTOS') or datos.get('impuestos', 0.0)).replace(',','')),
        'total': float(str(datos.get('TOTAL') or datos.get('total', 0.0)).replace(',','')),
        'moneda': datos.get('TOTAL_MONEDA') or datos.get('moneda') or 'USD',
        'es_remision': bool(datos.get('is_remission') or datos.get('es_remision', False)),
        'source_system': datos.get('SOURCE_SYSTEM') or datos.get('source_system') or 'UNKNOWN'
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
        text = TicketParserService.extraer_texto_desde_archivo(file_io, file_path.name)
    
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
            sanitized_datos = TicketParserService()._sanitize_for_json([obj.model_dump() for obj in valid_objects])
        elif datos.get('is_multi_pax'):
            valid_tickets = []
            for ticket in datos.get('tickets', []):
                mapped = map_legacy_to_schema(ticket)
                valid_tickets.append(BoletoAereoSchema(**mapped))
            sanitized_datos = TicketParserService()._sanitize_for_json([obj.model_dump() for obj in valid_tickets])
        else:
            mapped = map_legacy_to_schema(datos)
            valid_obj = BoletoAereoSchema(**mapped)
            sanitized_datos = TicketParserService()._sanitize_for_json(valid_obj.model_dump())
            
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

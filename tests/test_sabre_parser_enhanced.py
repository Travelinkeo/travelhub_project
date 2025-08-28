import os
import re
from core.ticket_parser import extract_data_from_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SABRE_DIR = os.path.join(PROJECT_ROOT, 'external_ticket_generator', 'SABRE')

# Sample files we expect to exist (adjust names if different)
SINGLE_FILE = '0457281019415.txt'
MULTI_FILE = '0577280309142.txt'


def read_ticket(filename: str):
    path = os.path.join(SABRE_DIR, filename)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def test_single_segment_sabre():
    text = read_ticket(SINGLE_FILE)
    data = extract_data_from_text(text)
    assert data['SOURCE_SYSTEM'] == 'SABRE'
    assert data.get('documento_identidad'), 'Debe extraer documento_identidad'
    assert data.get('fecha_emision_iso'), 'Debe contener fecha_emision_iso'
    assert len(data['vuelos']) == 1
    vuelo = data['vuelos'][0]
    assert vuelo.get('fecha_salida_iso') and re.match(r'\d{4}-\d{2}-\d{2}', vuelo['fecha_salida_iso'])
    assert vuelo.get('fecha_llegada_iso') and re.match(r'\d{4}-\d{2}-\d{2}', vuelo['fecha_llegada_iso'])
    assert vuelo.get('co2_valor'), 'Debe normalizar co2_valor'
    assert vuelo.get('co2_unidad') == 'kg'


def test_multi_segment_sabre():
    text = read_ticket(MULTI_FILE)
    data = extract_data_from_text(text)
    assert data['SOURCE_SYSTEM'] == 'SABRE'
    assert data.get('documento_identidad')
    assert data.get('fecha_emision_iso')
    assert len(data['vuelos']) >= 4  # permitir más si crece
    for vuelo in data['vuelos']:
        assert vuelo.get('fecha_salida_iso')
        assert vuelo.get('fecha_llegada_iso')
        # co2 puede variar pero si existe debe estar normalizado
        if 'co2_valor' in vuelo:
            assert re.match(r'^\d+(?:\.\d+)?$', vuelo['co2_valor'])
            assert vuelo.get('co2_unidad') == 'kg'


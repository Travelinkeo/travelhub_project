"""
Test Copa Parser con RECARGA FORZADA del módulo
"""
import os
import sys
import django
import json
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

# FORZAR RECARGA del módulo copa_parser
import core.parsers.copa_parser
importlib.reload(core.parsers.copa_parser)

from core.parsers.copa_parser import CopaParser

# Leer el boleto de Copa
file_path = r'C:\Users\ARMANDO\Downloads\Itinerary for Record Locator DYEXFG.eml'
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("="*80)
print("COPA PARSER - TEST CON RECARGA FORZADA")
print("="*80)

# Crear instancia del parser
parser = CopaParser()

# Verificar que puede parsear
can_parse = parser.can_parse(content)
print(f"\nPuede parsear: {can_parse}")

if not can_parse:
    print("ERROR: El parser no puede parsear este contenido")
    sys.exit(1)

# Parsear
print("\nParseando...")
result = parser.parse(content, content)

# Convertir a dict
result_dict = result.to_dict()

print("\n" + "="*80)
print("RESULTADOS")
print("="*80)

print(f"\nSistema: {result_dict.get('SOURCE_SYSTEM')}")
print(f"PNR: {result_dict.get('pnr')}")
print(f"Número de Boleto: {result_dict.get('numero_boleto')}")
print(f"Fecha de Emisión: {result_dict.get('fecha_emision')}")
print(f"Pasajero: {result_dict.get('pasajero', {}).get('nombre_completo')}")

agencia = result_dict.get('agencia', {})
print(f"\nAgencia: {agencia.get('nombre', 'N/A')}")
print(f"IATA: {agencia.get('iata', 'N/A')}")

vuelos = result_dict.get('vuelos', [])
print(f"\nNúmero de Vuelos: {len(vuelos)}")

for i, vuelo in enumerate(vuelos, 1):
    print(f"\nVuelo {i}:")
    print(f"  Aerolínea: {vuelo.get('aerolinea')}")
    print(f"  Número: {vuelo.get('numero_vuelo')}")
    print(f"  Origen: {vuelo.get('origen')}")
    print(f"  Destino: {vuelo.get('destino')}")
    print(f"  Salida: {vuelo.get('fecha_salida')} {vuelo.get('hora_salida')}")
    print(f"  Llegada: {vuelo.get('fecha_llegada')} {vuelo.get('hora_llegada')}")

# Guardar JSON
output_path = r'C:\Users\ARMANDO\travelhub_project\COPA_PARSER_TEST.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result_dict, f, indent=2, ensure_ascii=False)

print(f"\n✅ JSON guardado en: {output_path}")
print("\n" + "="*80)

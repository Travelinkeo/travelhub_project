import sys
import os
import logging
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path.cwd()))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
import django
django.setup()

from core.parsers.kiu_parser import KIUParser

# Configurar logging para ver print outputs
logging.basicConfig(level=logging.INFO)

text_from_log = """SAN ANTONIO V01187 G 2FEB 0850 0950 GPROMO 23K OK
CARACAS
PARA MAYOR INFORMACION INGRESAR AL SIGUIENTE LINK HTTP://WWW.CONVIASA.AERO/ES/"""

print("="*60)
print("VERIFICANDO KIU PARSER LOGIC")
print("="*60)

parser = KIUParser()
flights = parser._extract_flights(text_from_log)

print(f"\nResulting Flights ({len(flights)}):")
for f in flights:
    print(f)

if not flights:
    print("\n❌ STILL NO FLIGHTS EXTRACTED!")
else:
    print("\n✅ SUCCESS - FLIGHTS EXTRACTED")


import os
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.kiu_parser import KIUParser

print("🚀 Iniciando Simulación del Parser Mejorado...")

parser = KIUParser()

casos = [
    {
        "nombre": "Caso 1: Estándar USD",
        "texto": """
        KIUSYS.COM
        TICKET NO: 123
        FARE: USD 90.00
        TOTAL: USD 100.00
        """,
        "esperado_total": "100.00",
        "esperado_moneda": "USD"
    },
    {
        "nombre": "Caso 2: VES Desordenado",
        "texto": """
        KIUSYS.COM
        TICKET NO: 1234567890
        ALGUN TEXTO RARO
        TOTAL : VES
        OTRA LINEA
        5,432.10
        """,
        "esperado_total": "5432.10",
        "esperado_moneda": "VES"
    },
    {
        "nombre": "Caso 3: Formato Europeo (1.234,56)",
        "texto": """
        KIUSYS.COM
        TOTAL EUROS 1.250,50
        """,
        "esperado_total": "1250.50",
        "esperado_moneda": "EUR"
    },
    {
        "nombre": "Caso 4: Ruido Numérico (Ignorar fechas)",
        "texto": """
        ISSUED: 2025
        FLIGHT 2024
        TOTAL A PAGAR: 500.00
        """,
        "esperado_total": "500.00",
        "esperado_moneda": "USD" # Default
    }
]

for caso in casos:
    print(f"\n--- Probando: {caso['nombre']} ---")
    resultado = parser._extract_amounts(caso['texto'])
    
    total_obtenido = resultado['total_amount']
    moneda_obtenida = resultado['currency']
    
    print(f"   Obtenido: {moneda_obtenida} {total_obtenido}")
    
    if total_obtenido == caso['esperado_total'] and moneda_obtenida == caso['esperado_moneda']:
        print("   ✅ PASÓ")
    else:
        print(f"   ❌ FALLÓ (Esperaba {caso['esperado_moneda']} {caso['esperado_total']})")

print("\nSimulación finalizada.")

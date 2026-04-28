import os
import sys
import django
import json

# Setup Django environment
sys.path.append(r'C:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import generate_ticket
from core.models import Agencia

def generate_examples():
    # Mock data based on the Turkish Airlines example from previous user messages
    data = {
        "pnr": "FQTTPH",
        "SOURCE_SYSTEM": "SABRE",
        "NOMBRE_DEL_PASAJERO": "QUINTERO RAMIREZ/JHONY ALBERTO",
        "TICKET": "235-1234567890",
        "FECHA_EMISION": "25 OCT 26",
        "TARIFA": "1,250.00",
        "TOTAL": "1,450.00",
        "moneda": "USD",
        "vuelos": [
            {
                "numero_vuelo": "TK 224",
                "origen": "CCS",
                "destino": "IST",
                "fecha_salida": "20APR26",
                "hora_salida": "23:10",
                "hora_llegada": "17:50",
                "clase": "Y",
                "cabina": "TURISTA",
                "equipaje": "2PC",
                "aerolinea": "TURKISH AIRLINES",
                "status": "CONFIRMADO"
            },
            {
                "numero_vuelo": "TK 26",
                "origen": "IST",
                "destino": "PVG",
                "fecha_salida": "22APR26",
                "hora_salida": "01:30",
                "hora_llegada": "16:45",
                "clase": "Y",
                "cabina": "TURISTA",
                "equipaje": "2PC",
                "aerolinea": "TURKISH AIRLINES",
                "status": "CONFIRMADO"
            }
        ]
    }

    # Get a real agency or mock one
    agencia = Agencia.objects.first()
    if not agencia:
        print("No agency found in database. Creating a mock one in memory...")
        agencia = Agencia(nombre="TRAVELHUB PREVIEWS", plantilla_boletos='m1')

    # Output directory for artifacts
    output_dir = r'C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d'
    
    models = ['m1', 'm2', 'm3', 'm4', 'm5']
    filenames = {
        'm1': 'M1_Standard_Corporate.pdf',
        'm2': 'M2_Editorial_Plus.pdf',
        'm3': 'M3_Executive_Compact.pdf',
        'm4': 'M4_Timeline_Pro.pdf',
        'm5': 'M5_Modern_Tech.pdf'
    }

    for model in models:
        print(f"Generating preview for {model}...")
        agencia.plantilla_boletos = model
        # Force the template selection by passing the modified agency object
        pdf_bytes, filename = generate_ticket(data, agencia_obj=agencia)
        
        output_path = os.path.join(output_dir, filenames[model])
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        print(f"Saved to {output_path}")

if __name__ == "__main__":
    generate_examples()

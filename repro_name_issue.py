
import sys
import os
import django

# Setup Django
sys.path.append('c:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core.ticket_parser import _get_nombre_completo_pasajero

def test_name_extraction(boleto_id):
    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        texto = boleto.archivo_boleto.read().decode('utf-8', errors='ignore')
        print(f"--- TEXTO DE BOLETO {boleto_id} ---")
        # print(texto[:1000]) # Snippet
        
        nombre = _get_nombre_completo_pasajero(texto)
        print(f"\nRESULTADO: '{nombre}'")
        
        # Test individual strategies if possible or just log matches
        import re
        blacklist = [
            'DATE/FECHA', 'FECHA/EMISION', 'NAME/NOMBRE', 'AGENT/AGENTE', 'FROM/TO', 'DESDE/HACIA', 'AIR/FARE', 
            'TELEFONO', 'PHONE', 'MAIL', 'CORREO', 'DOCUMENTO',
            'FECHA DE EMISION', 'DATE OF ISSUE', 'FECHA', 'DATE',
            'ISSUING AIRLINE', 'LINEA AEREA EMISORA', 'EMISORA', 'AIRLINE'
        ]
        
        print("\n--- ANALISIS DE MATCHES ---")
        matches = re.finditer(r'\b([A-Z]{2,}(?: [A-Z]+)*/[A-Z]{2,}(?: [A-Z]+)*)\b', texto)
        for i, match in enumerate(matches):
            candidate = match.group(1).strip()
            is_blacklisted = any(bad in candidate.upper() for bad in blacklist)
            print(f"Match {i}: '{candidate}' | Blacklisted: {is_blacklisted}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_name_extraction(1025)


import os
import sys
import json
import django
import io

# Preparar entorno Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text
from core.services.ticket_parser_service import TicketParserService

def test_avior_eml():
    eml_path = r"C:\Users\ARMANDO\Downloads\Tickets Avior Airlines.eml"
    if not os.path.exists(eml_path):
        print(f"Error: No existe el archivo {eml_path}")
        return

    print(f"--- INICIANDO TEST DE PARSEO: {eml_path} ---")
    
    # 1. Extraer texto usando el servicio oficial (que ahora debería limpiar HTML)
    try:
        with open(eml_path, 'rb') as f:
            # TicketParserService.extraer_texto_desde_archivo(file_obj, filename)
            texto_limpio = TicketParserService.extraer_texto_desde_archivo(f, eml_path)
        
        print(f"Longitud del texto extraído: {len(texto_limpio)}")
        
        # Guardar para inspección
        with open("last_extraction_debug.txt", "w", encoding="utf-8") as f:
            f.write(texto_limpio)
        print("Texto extraído guardado en last_extraction_debug.txt")
            
    except Exception as e:
        import traceback
        print(f"Error extrayendo texto: {e}")
        traceback.print_exc()
        return

    # 2. Parsear usando la IA
    try:
        # extract_data_from_text(plain_text, html_text="", pdf_path=None)
        # Pasamos el texto limpio como plain_text
        resultado = extract_data_from_text(texto_limpio, pdf_path=eml_path)
        print("\n--- RESULTADO DEL PARSEO ---")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        # Verificar campo específico de nombre
        if isinstance(resultado, dict):
            pax = resultado.get('NOMBRE_DEL_PASAJERO')
            print(f"\nNOMBRE_DEL_PASAJERO detectado: '{pax}'")
            
            vuelos = resultado.get('vuelos', [])
            print(f"SEGMENTOS detectados: {len(vuelos)}")
            for i, v in enumerate(vuelos):
                print(f"  [{i}] {v.get('origen')} -> {v.get('destino')} ({v.get('fecha_salida')})")
            
    except Exception as e:
        import traceback
        print(f"Error parseando: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_avior_eml()

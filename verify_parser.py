import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.ticket_parser_service import TicketParserService

try:
    print("--- INICIO VERIFICACION ---")
    service = TicketParserService()
    # procesar_boleto returns a Venta object or string, but updates BoletoImportado
    resultado = service.procesar_boleto(1010)
    print(f"Resultado procesamiento: {resultado}")
    
    # Fetch the BoletoImportado to see the parsed data
    from core.models import BoletoImportado
    boleto = BoletoImportado.objects.get(id_boleto_importado=1010)
    data = boleto.datos_parseados
    
    vuelos = data.get('vuelos', [])
    print(f"Segmentos encontrados: {len(vuelos)}")
    if vuelos:
        print(json.dumps(vuelos, indent=2, default=str))
    else:
        print("No se encontraron vuelos.")
        print("Itinerario crudo:")
        print(data.get('ItinerarioFinalLimpio'))
    print("--- FIN VERIFICACION ---")
except Exception as e:
    print(f"Error: {e}")

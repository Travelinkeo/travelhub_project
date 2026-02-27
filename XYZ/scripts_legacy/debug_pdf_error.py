import os
import django
import sys
from django.core.files.base import ContentFile

sys.path.append(r"C:\Users\ARMANDO\travelhub_project")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core.ticket_parser import generate_ticket

# Buscar el boleto problemático
ticket_num = "742-0307421552"
boleto = BoletoImportado.objects.filter(numero_boleto=ticket_num).first()

if not boleto:
    print(f"Boleto {ticket_num} no encontrado en DB.")
    # Buscar el más reciente por si acaso
    print("Buscando último boleto...")
    boleto = BoletoImportado.objects.last()

if boleto:
    print(f"Probando generar PDF para Boleto ID {boleto.pk} - {boleto.numero_boleto}")
    print("Datos Parseados (Keys):", boleto.datos_parseados.keys())
    vuelos = boleto.datos_parseados.get('vuelos')
    print(f"Vuelos: {vuelos}")
    if vuelos:
        print(f"Tipo Vuelos: {type(vuelos)}")
        if isinstance(vuelos, list) and len(vuelos) > 0:
            print(f"Elemento 0 tipo: {type(vuelos[0])}")
    
    agente = boleto.datos_parseados.get('agente_emisor')
    print(f"Agente Emisor: {agente}")
    direccion = boleto.datos_parseados.get('direccion_aerolinea')
    print(f"Direccion Aerolinea: {direccion}")
    
    try:
        pdf_bytes, filename = generate_ticket(boleto.datos_parseados)
        print(f"Resultado: Filename={filename}, BytesType={type(pdf_bytes)}")
        if isinstance(pdf_bytes, bytes):
             print(f"Bytes Length: {len(pdf_bytes)}")
        else:
             print(f"ERROR: pdf_bytes NO ES BYTES. Es {type(pdf_bytes)}: {pdf_bytes}")

    except Exception as e:
        print(f"Excepción Generando PDF: {e}")
        import traceback
        with open('error_log.txt', 'w', encoding='utf-8') as f:
            traceback.print_exc(file=f)

else:
    print("No hay boletos en la DB.")

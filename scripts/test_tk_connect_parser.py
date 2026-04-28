"""
Script de prueba para parser y generación de PDF de TK Connect
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import fitz
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
import django
django.setup()

from core.tk_connect_parser import parse_tk_connect_ticket
from django.template.loader import render_to_string
from weasyprint import HTML
import re


def extraer_codigo_ciudad(texto):
    """Extrae el código IATA de una ciudad (ej: 'Caracas (CCS)' -> 'CCS')"""
    match = re.search(r'\(([A-Z]{3})\)', texto)
    return match.group(1) if match else ''


def generar_pdf_tk_connect(pdf_path):
    """Genera un PDF formateado desde un boleto de TK Connect"""
    
    # Extraer texto del PDF
    doc = fitz.open(pdf_path)
    text = '\n'.join([page.get_text() for page in doc])
    doc.close()
    
    print("Texto extraido del PDF:")
    print("=" * 80)
    print(text[:500])
    print("=" * 80)
    
    # Parsear el boleto
    data = parse_tk_connect_ticket(text)
    
    print("\nDatos parseados:")
    print("=" * 80)
    for key, value in data.items():
        if key != 'vuelos':
            print(f"{key}: {value}")
    print(f"\nVuelos encontrados: {len(data['vuelos'])}")
    for i, vuelo in enumerate(data['vuelos'], 1):
        print(f"\nVuelo {i}:")
        for k, v in vuelo.items():
            print(f"  {k}: {v}")
    print("=" * 80)
    
    # Enriquecer datos para la plantilla
    for vuelo in data['vuelos']:
        vuelo['origen_codigo'] = extraer_codigo_ciudad(vuelo['origen'])
        vuelo['destino_codigo'] = extraer_codigo_ciudad(vuelo['destino'])
    
    # Preparar contexto para la plantilla
    context = {
        'pasajero': {
            'nombre_completo': data['pasajero'].get('nombre_completo', 'N/A'),
            'documento_identidad': data['pasajero'].get('telefono', 'N/A')
        },
        'reserva': {
            'codigo_reservacion': data['pnr'],
            'numero_boleto': data['numero_boleto'],
            'fecha_emision': data['fecha_creacion'],
            'aerolinea_emisora': 'Turkish Airlines',
            'agente_emisor': {'numero_iata': data['oficina_emision']}
        },
        'itinerario': {
            'vuelos': [{
                'fecha_salida': v['fecha_salida'],
                'aerolinea': 'Turkish Airlines',
                'numero_vuelo': v['numero_vuelo'],
                'origen': {'ciudad': v['origen']},
                'hora_salida': v['hora_salida'],
                'destino': {'ciudad': v['destino']},
                'hora_llegada': v['hora_llegada'],
                'cabina': v['cabina']
            } for v in data['vuelos']]
        }
    }
    
    # Renderizar HTML
    html_content = render_to_string('core/tickets/ticket_template_tk_connect.html', context)
    
    # Generar PDF
    output_path = Path(__file__).parent.parent / 'media' / 'boletos_generados' / f'TK_Connect_{data["pnr"]}.pdf'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    HTML(string=html_content).write_pdf(output_path)
    
    print(f"\n✅ PDF generado exitosamente: {output_path}")
    return output_path


if __name__ == '__main__':
    pdf_path = r'C:\Users\ARMANDO\travelhub_project\OTRA CARPETA\VW6FHY.pdf'
    generar_pdf_tk_connect(pdf_path)

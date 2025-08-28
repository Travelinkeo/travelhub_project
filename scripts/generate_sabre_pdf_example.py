import os
import sys
import json

# Asegurar ruta del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.ticket_parser import extract_data_from_text
from core.pdf_generator import generate_ticket_pdf as legacy_generate_ticket_pdf

DEFAULT_SAMPLE = '0457281019415.txt'
SABRE_DIR = os.path.join(BASE_DIR, 'external_ticket_generator', 'SABRE')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Genera PDF de un boleto Sabre (texto plano).')
    parser.add_argument('archivo', nargs='?', default=DEFAULT_SAMPLE, help='Nombre de archivo .txt en carpeta SABRE')
    args = parser.parse_args()

    target = os.path.join(SABRE_DIR, args.archivo)
    if not os.path.exists(target):
        print(f"No se encontró archivo en {target}")
        return

    with open(target, 'r', encoding='utf-8') as f:
        plain_text = f.read()

    print('--- Iniciando parseo Sabre (texto plano copiado) ---')
    parsed = extract_data_from_text(plain_text, '')

    # Forzar SOURCE_SYSTEM a SABRE_PDF para usar transform en pdf_generator si se desea
    parsed['SOURCE_SYSTEM'] = 'SABRE_PDF'

    print('\n--- Datos Parseados (resumen) ---')
    resumen = {
        'pasajero': parsed.get('preparado_para'),
        'codigo_reservacion': parsed.get('codigo_reservacion'),
        'numero_boleto': parsed.get('numero_boleto'),
        'fecha_emision': parsed.get('fecha_emision'),
        'vuelos_count': len(parsed.get('vuelos', [])),
        'archivo': args.archivo,
    }
    print(json.dumps(resumen, ensure_ascii=False, indent=2))

    # Generar PDF
    try:
        pdf_bytes, filename = legacy_generate_ticket_pdf(parsed)
    except Exception as e:
        print('Error generando PDF:', e)
        return

    out_dir = os.path.join(BASE_DIR, 'media', 'boletos_generados')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    with open(out_path, 'wb') as f:
        f.write(pdf_bytes)
    print(f'PDF generado: {out_path}')

    # Guardar JSON completo para inspección
    json_out = os.path.join(out_dir, filename.replace('.pdf', '.json'))
    with open(json_out, 'w', encoding='utf-8') as jf:
        json.dump(parsed, jf, ensure_ascii=False, indent=2)
    print(f'JSON guardado: {json_out}')

if __name__ == '__main__':
    main()

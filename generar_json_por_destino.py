import PyPDF2
import json

pdf_path = "TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf"
reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))

# Definir rangos de páginas por destino (índice 0)
destinos = {
    'isla_margarita': {'inicio': 6, 'fin': 54, 'nombre': 'Isla Margarita y Coche'},
    'maiquetia': {'inicio': 54, 'fin': 64, 'nombre': 'Maiquetia'},
    'caracas': {'inicio': 64, 'fin': 83, 'nombre': 'Caracas'},
    'los_roques': {'inicio': 83, 'fin': 117, 'nombre': 'Los Roques'},
    'morrocoy': {'inicio': 117, 'fin': 123, 'nombre': 'Morrocoy'},
    'canaima': {'inicio': 123, 'fin': 131, 'nombre': 'Canaima'},
    'merida': {'inicio': 131, 'fin': 138, 'nombre': 'Mérida'}
}

for key, info in destinos.items():
    paginas = []
    for i in range(info['inicio'], info['fin']):
        try:
            page = reader.pages[i]
            texto = page.extract_text()
            paginas.append({
                'numero_pagina': i + 1,
                'texto': texto
            })
        except:
            pass
    
    # Guardar JSON
    output = {
        'destino': info['nombre'],
        'proveedor': 'BT Travel',
        'vigencia_tarifario': 'Sep 2025 - Feb 2026',
        'total_paginas': len(paginas),
        'paginas': paginas
    }
    
    filename = f'tarifario_{key}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"OK {filename}: {len(paginas)} paginas")

print("\nJSONs generados por destino")

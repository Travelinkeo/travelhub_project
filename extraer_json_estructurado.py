import PyPDF2
import json
import re
from pathlib import Path

# Configuración
PDF_PATH = r"C:\Users\ARMANDO\travelhub_project\TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf"
OUTPUT_DIR = Path("tarifarios_json_estructurados")
OUTPUT_DIR.mkdir(exist_ok=True)

# Rangos de páginas por destino
DESTINOS = {
    'isla_margarita': {'inicio': 6, 'fin': 54, 'nombre': 'Isla Margarita'},
    'maiquetia': {'inicio': 54, 'fin': 64, 'nombre': 'Maiquetía'},
    'caracas': {'inicio': 64, 'fin': 83, 'nombre': 'Caracas'},
    'los_roques': {'inicio': 83, 'fin': 117, 'nombre': 'Los Roques'},
    'morrocoy': {'inicio': 117, 'fin': 123, 'nombre': 'Morrocoy'},
    'canaima': {'inicio': 123, 'fin': 131, 'nombre': 'Canaima'},
    'merida': {'inicio': 131, 'fin': 138, 'nombre': 'Mérida'}
}

def extraer_hoteles_de_texto(texto, destino):
    """Extrae hoteles del texto de múltiples páginas"""
    hoteles = []
    
    # Patrones para detectar hoteles
    patron_hotel = r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{10,50})\s*(?:TARIFA|AGENCIAS)\s+COMISIONABLE\s+AL\s+(\d+)%'
    
    # Buscar todos los hoteles
    for match in re.finditer(patron_hotel, texto):
        nombre = match.group(1).strip()
        comision = match.group(2)
        
        # Extraer régimen
        regimen = 'SOLO DESAYUNO'
        if 'TODO INCLUIDO' in texto[match.start():match.start()+500]:
            regimen = 'TODO INCLUIDO'
        elif 'PENSIÓN COMPLETA' in texto[match.start():match.start()+500] or 'PENSION COMPLETA' in texto[match.start():match.start()+500]:
            regimen = 'PENSION COMPLETA'
        elif 'MEDIA PENSIÓN' in texto[match.start():match.start()+500]:
            regimen = 'MEDIA PENSION'
        elif 'FULL PENSIÓN' in texto[match.start():match.start()+500]:
            regimen = 'PENSION COMPLETA'
        
        # Extraer moneda
        moneda = 'USD'
        if '€' in texto[match.start():match.start()+1000]:
            moneda = 'EUR'
        
        # Extraer tarifas (simplificado - buscar números después del hotel)
        texto_hotel = texto[match.start():match.start()+2000]
        tarifas_encontradas = re.findall(r'\$?\€?(\d{2,3})[,\.]?(\d{2})?', texto_hotel)
        
        habitaciones = []
        if tarifas_encontradas:
            # Crear habitación STANDARD con tarifas encontradas
            tarifas = []
            
            # Temporada baja (primera tarifa encontrada)
            if len(tarifas_encontradas) >= 2:
                sgl = f"{tarifas_encontradas[0][0]}.{tarifas_encontradas[0][1] or '00'}"
                dbl = f"{tarifas_encontradas[1][0]}.{tarifas_encontradas[1][1] or '00'}"
                
                tarifas.append({
                    'fecha_inicio': '2025-09-21',
                    'fecha_fin': '2025-12-20',
                    'temporada': 'TEMPORADA BAJA',
                    'moneda': moneda,
                    'sgl': sgl,
                    'dbl': dbl
                })
            
            habitaciones.append({
                'tipo': 'STANDARD',
                'capacidad_adultos': 2,
                'capacidad_ninos': 0,
                'capacidad_total': 2,
                'tarifas': tarifas
            })
        
        if habitaciones:
            hoteles.append({
                'nombre': nombre,
                'destino': destino,
                'regimen': regimen,
                'comision': comision,
                'habitaciones': habitaciones
            })
    
    return hoteles

def procesar_pdf():
    """Procesa el PDF y genera JSONs estructurados por destino"""
    print(f"Abriendo PDF: {PDF_PATH}")
    
    with open(PDF_PATH, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        total_paginas = len(reader.pages)
        print(f"Total de paginas: {total_paginas}")
        
        for destino_key, config in DESTINOS.items():
            print(f"\nProcesando {config['nombre']}...")
            
            # Extraer texto de todas las páginas del destino
            texto_completo = ""
            for i in range(config['inicio'], min(config['fin'], total_paginas)):
                page = reader.pages[i]
                texto_completo += page.extract_text() + "\n"
            
            # Extraer hoteles
            hoteles = extraer_hoteles_de_texto(texto_completo, config['nombre'])
            
            if hoteles:
                # Crear JSON estructurado
                json_data = {
                    'nombre_tarifario': 'Tarifario Nacional Septiembre 2025',
                    'destino': config['nombre'],
                    'vigencia': {
                        'inicio': '2025-09-21',
                        'fin': '2026-01-15'
                    },
                    'comision_estandar': '15.00',
                    'hoteles': hoteles
                }
                
                # Guardar JSON
                output_file = OUTPUT_DIR / f"tarifario_{destino_key}_estructurado.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                print(f"  - {len(hoteles)} hoteles extraidos")
                print(f"  - Guardado en: {output_file}")
            else:
                print(f"  - No se encontraron hoteles")

if __name__ == '__main__':
    procesar_pdf()
    print("\n¡Proceso completado!")
    print(f"Archivos generados en: {OUTPUT_DIR}")

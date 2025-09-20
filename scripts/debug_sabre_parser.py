import os
import sys
import json
import fitz  # PyMuPDF
import time
from pathlib import Path

# --- Configuración del Entorno de Django ---
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
import django
django.setup()

# --- Importar el Parser ---
from core.sabre_parser import parse_sabre_ticket

# --- Configuración ---
DIRECTORIO_PRUEBAS = project_root / 'sabre_test_cases'

def leer_contenido_boleto(ruta_archivo: Path):
    """Lee el contenido de un archivo de boleto (PDF o TXT)."""
    try:
        if ruta_archivo.suffix.lower() == '.pdf':
            with fitz.open(ruta_archivo) as doc:
                return "".join(page.get_text("text") for page in doc)
        else:
            return ruta_archivo.read_text(encoding='utf-8')
    except Exception as e:
        print(f"    ❌ Error al leer el archivo: {e}")
        return None

def procesar_archivo(ruta_completa: Path):
    """Procesa un único archivo de boleto y muestra el resultado."""
    print("=" * 70)
    print(f"📄 Procesando archivo: {ruta_completa.name}")
    print("=" * 70)
    
    contenido_texto = leer_contenido_boleto(ruta_completa)
    if not contenido_texto:
        print("    ❌ No se pudo leer el contenido del boleto.")
        return False

    datos_parseados = parse_sabre_ticket(contenido_texto)

    if datos_parseados and 'error' not in datos_parseados and datos_parseados.get('itinerario', {}).get('vuelos'):
        print("    ✅ ¡Parseo exitoso!")
        print(json.dumps(datos_parseados, indent=4, ensure_ascii=False))
        return True
    else:
        print("    ❌ Fallo en el parseo.")
        print(f"    Resultado: {json.dumps(datos_parseados, indent=4, ensure_ascii=False)}")
        return False

def main():
    """
    Función principal del script de depuración.
    - Si se pasa un nombre de archivo como argumento, procesa solo ese archivo.
    - Si no, procesa todos los archivos .pdf y .txt en el directorio de pruebas.
    """
    print("--- INICIANDO SCRIPT DE DEPURACIÓN DE SABRE ---")
    
    if not DIRECTORIO_PRUEBAS.is_dir():
        print(f"❌ ERROR: El directorio de pruebas no existe: {DIRECTORIO_PRUEBAS}")
        return

    # --- Decidir qué archivos procesar ---
    archivos_a_probar = []
    if len(sys.argv) > 1:
        # Modo: Archivo único
        nombre_archivo = sys.argv[1]
        ruta_archivo = DIRECTORIO_PRUEBAS / nombre_archivo
        if not ruta_archivo.exists():
            print(f"❌ ERROR: El archivo especificado no existe: {ruta_archivo}")
            return
        archivos_a_probar.append(ruta_archivo)
    else:
        # Modo: Batch (todos los archivos)
        print("Modo Batch: Analizando todos los archivos en 'sabre_test_cases'...")
        archivos_a_probar = list(DIRECTORIO_PRUEBAS.glob('*.pdf')) + list(DIRECTORIO_PRUEBAS.glob('*.txt'))

    if not archivos_a_probar:
        print("❌ No se encontraron archivos .pdf o .txt para probar.")
        return

    print(f"✅ Encontrados {len(archivos_a_probar)} boletos para analizar.\n")
    
    resultados = {'exitosos': 0, 'fallidos': 0}
    
    for ruta_archivo in archivos_a_probar:
        if procesar_archivo(ruta_archivo):
            resultados['exitosos'] += 1
        else:
            resultados['fallidos'] += 1
        time.sleep(0.1)

    print("\n\n--- RESUMEN FINAL DE LA PRUEBA ---")
    print(f"Total de archivos procesados: {len(archivos_a_probar)}")
    print(f"✅ Exitosos: {resultados['exitosos']}")
    print(f"❌ Fallidos: {resultados['fallidos']}")
    print("--- FIN DEL SCRIPT DE DEPURACIÓN ---")

if __name__ == "__main__":
    main()
"""
Script para mover archivos obsoletos a scripts_archive/deprecated/
"""
import os
import shutil
from pathlib import Path

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEPRECATED_DIR = BASE_DIR / 'scripts_archive' / 'deprecated'

# Archivos a mover
OBSOLETE_FILES = {
    'monitores': [
        'core/email_monitor.py',
        'core/email_monitor_v2.py',
        'core/email_monitor_whatsapp_drive.py',
    ],
    'tests_email_whatsapp': [
        'test_email_con_adjunto.py',
        'test_email_connection.py',
        'test_email_simple.py',
        'test_monitor_email.py',
        'test_monitor_whatsapp.py',
        'test_whatsapp_boleto.py',
        'test_whatsapp_directo.py',
        'test_whatsapp_drive.py',
        'test_whatsapp_simple.py',
    ],
    'tests_parsers': [
        'test_amadeus_parser.py',
        'test_copa_sprk.py',
        'test_wingo.py',
    ],
    'scripts_procesamiento': [
        'enviar_email_boleto_41.py',
        'enviar_pdf_drive_whatsapp.py',
        'enviar_pdf_whatsapp_ngrok.py',
        'enviar_pdf_whatsapp_simple.py',
        'generar_pdf_amadeus_nuevo.py',
        'generar_pdf_amadeus.py',
        'generar_pdf_copa.py',
        'generar_pdf_wingo.py',
        'marcar_y_procesar_kiu.py',
        'procesar_correo_kiu_ahora.py',
        'procesar_ultimo_correo_kiu.py',
        'test_procesar_correo_kiu.py',
    ],
    'scripts_verificacion': [
        'verificar_correo_kiu.py',
        'verificar_error_twilio.py',
        'verificar_ultimo_boleto.py',
        'verificar_ultimo_proceso.py',
    ],
    'documentos': [
        'CAMBIOS_SEGURIDAD_IMPLEMENTADOS.md',
        'ESTADO_ACTUAL_PROYECTO.md',
        'INFORME_ANALISIS_CODIGO.md',
        'PLAN_MEJORAS.md',
        'REFACTORIZACION_COMPLETADA.md',
        'RESUMEN_EJECUTIVO_ANALISIS.md',
    ],
}

def move_files():
    """Mueve archivos obsoletos a deprecated/"""
    
    # Crear directorio deprecated si no existe
    DEPRECATED_DIR.mkdir(parents=True, exist_ok=True)
    
    moved_count = 0
    not_found = []
    errors = []
    
    print("=" * 60)
    print("MOVIENDO ARCHIVOS OBSOLETOS")
    print("=" * 60)
    
    for category, files in OBSOLETE_FILES.items():
        print(f"\n[{category}]")
        
        # Crear subcarpeta para la categoría
        category_dir = DEPRECATED_DIR / category
        category_dir.mkdir(exist_ok=True)
        
        for file_path in files:
            source = BASE_DIR / file_path
            
            # Determinar destino
            if '/' in file_path:
                # Archivo en subdirectorio (ej: core/email_monitor.py)
                dest = category_dir / Path(file_path).name
            else:
                # Archivo en raíz
                dest = category_dir / file_path
            
            if source.exists():
                try:
                    shutil.move(str(source), str(dest))
                    print(f"  OK: {file_path} -> {dest.relative_to(BASE_DIR)}")
                    moved_count += 1
                except Exception as e:
                    print(f"  ERROR: {file_path}: {e}")
                    errors.append((file_path, str(e)))
            else:
                print(f"  SKIP: {file_path} (no encontrado)")
                not_found.append(file_path)
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Archivos movidos: {moved_count}")
    print(f"Archivos no encontrados: {len(not_found)}")
    print(f"Errores: {len(errors)}")
    
    if not_found:
        print("\nArchivos no encontrados:")
        for f in not_found:
            print(f"  - {f}")
    
    if errors:
        print("\nErrores:")
        for f, e in errors:
            print(f"  - {f}: {e}")
    
    print(f"\nArchivos movidos a: {DEPRECATED_DIR.relative_to(BASE_DIR)}")
    print("\nProceso completado")

if __name__ == '__main__':
    move_files()

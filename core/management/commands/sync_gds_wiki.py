import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Sincroniza manuales técnicos GDS desde el escritorio del usuario a la Wiki interna de TravelHub.'

    def handle(self, *args, **options):
        # Rutas identificadas en la conversación
        user_desktop_source = Path(r'C:\Users\ARMANDO\Desktop\Referencias GDS')
        project_wiki_root = Path(settings.BASE_DIR) / 'docs' / 'wiki' / 'GDS'

        if not user_desktop_source.exists():
            self.stdout.write(self.style.ERROR(f'❌ Error: No se encontró la carpeta en el escritorio: {user_desktop_source}'))
            self.stdout.write(self.style.WARNING('Por favor, asegúrate de que la carpeta "Referencias GDS" esté en tu escritorio.'))
            return

        self.stdout.write(self.style.SUCCESS(f'🚀 Iniciando sincronización de conocimiento desde {user_desktop_source}...'))

        # Asegurar que el destino existe
        project_wiki_root.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        errors_count = 0
        
        # Diccionario para normalizar nombres de carpetas GDS
        gds_mapping = {
            'AMADEUS': 'AMADEUS',
            'SABRE': 'SABRE',
            'KIU': 'KIU'
        }

        # Recorrer carpetas en el escritorio
        for entry in os.scandir(user_desktop_source):
            if entry.is_dir():
                folder_name = entry.name.upper()
                
                # Identificar si es una carpeta de GDS conocida o crearla
                target_folder_name = gds_mapping.get(folder_name, folder_name)
                target_dir = project_wiki_root / target_folder_name
                target_dir.mkdir(exist_ok=True)

                self.stdout.write(f'📂 Procesando categoría: {target_folder_name}')
                
                # Sincronizar archivos .md, .txt y .pdf (como backup)
                for file_entry in os.scandir(entry.path):
                    if file_entry.is_file():
                        filename = file_entry.name
                        ext = Path(filename).suffix.lower()
                        
                        # Solo procesamos archivos de texto/markdown para la Wiki interactiva
                        if ext in ['.md', '.txt']:
                            # Si es .txt, lo convertimos a .md para el lector
                            clean_filename = filename if ext == '.md' else filename.replace('.txt', '.md')
                            dest_path = target_dir / clean_filename
                            
                            try:
                                shutil.copy2(file_entry.path, dest_path)
                                self.stdout.write(self.style.SUCCESS(f'  [OK] {clean_filename}'))
                                copied_count += 1
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f'  [ERR] No se pudo copiar {filename}: {str(e)}'))
                                errors_count += 1
                        
                        elif ext == '.pdf':
                            # Los PDFs se copian como referencia pero el lector web no los muestra aún
                            dest_path = target_dir / filename
                            try:
                                shutil.copy2(file_entry.path, dest_path)
                                self.stdout.write(f'  [REF] {filename} (PDF copiado)')
                                copied_count += 1
                            except Exception as e:
                                errors_count += 1

        self.stdout.write('\n' + '='*40)
        self.stdout.write(self.style.SUCCESS(f'✅ Sincronización Finalizada.'))
        self.stdout.write(f'- Archivos procesados: {copied_count}')
        if errors_count > 0:
            self.stdout.write(self.style.WARNING(f'- Errores encontrados: {errors_count}'))
        self.stdout.write('='*40)
        self.stdout.write('La Wiki GDS interactiva se ha actualizado con el nuevo conocimiento.')

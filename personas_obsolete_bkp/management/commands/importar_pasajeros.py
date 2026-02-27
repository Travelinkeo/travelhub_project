
import pandas as pd
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from personas.models import Pasajero
import os

class Command(BaseCommand):
    help = 'Importa pasajeros desde un archivo Excel. Las columnas esperadas son Apellido, Nombre, Numero de Documento.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='La ruta absoluta al archivo Excel.')

    def handle(self, *args, **options):
        file_path = options['file_path']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'El archivo no se encuentra en la ruta: {file_path}'))
            return

        try:
            df = pd.read_excel(file_path)
            self.stdout.write(self.style.SUCCESS(f'Archivo Excel leído correctamente. Se encontraron {len(df)} filas.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al leer el archivo Excel: {e}'))
            return

        # Validar que las columnas esperadas existan
        required_columns = ['Apellido', 'Nombre', 'Numero de Documento']
        if not all(col in df.columns for col in required_columns):
            self.stdout.write(self.style.ERROR(
                f'El archivo Excel debe contener las siguientes columnas: {", ".join(required_columns)}'
            ))
            return

        created_count = 0
        updated_count = 0

        for index, row in df.iterrows():
            nombre = row['Nombre']
            apellido = row['Apellido']
            numero_documento = row['Numero de Documento']

            if not all([nombre, apellido, numero_documento]):
                self.stdout.write(self.style.WARNING(f'Fila {index + 2} omitida por tener datos faltantes.'))
                continue
            
            # Convertir a string para asegurar consistencia
            numero_documento = str(numero_documento)

            try:
                pasajero, created = Pasajero.objects.update_or_create(
                    numero_documento=numero_documento,
                    defaults={
                        'nombres': str(nombre).strip(),
                        'apellidos': str(apellido).strip(),
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Creado: {pasajero.nombres} {pasajero.apellidos} ({pasajero.numero_documento})'))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.NOTICE(f'Actualizado: {pasajero.nombres} {pasajero.apellidos} ({pasajero.numero_documento})'))

            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f'Error de validación en la fila {index + 2}: {e.messages}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error inesperado en la fila {index + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Proceso completado. Pasajeros creados: {created_count}, Pasajeros actualizados: {updated_count}.'))

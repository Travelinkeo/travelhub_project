import base64
from django.core.management.base import BaseCommand
from core.models import Agencia

class Command(BaseCommand):
    help = 'Migra los logos (ImageField o base64 general) a logo_pdf_base64 para uso en reportes PDF'

    def handle(self, *args, **options):
        agencias = Agencia.objects.all()
        migradas = 0
        errores = 0

        for agencia in agencias:
            try:
                logo_generado = False
                # Generar el logo_pdf_base64 desde el logo (ImageField) si existe
                if agencia.logo:
                    try:
                        with agencia.logo.open('rb') as f:
                            encoded_string = base64.b64encode(f.read()).decode('utf-8')
                        agencia.logo_pdf_base64 = encoded_string
                        agencia.save(update_fields=['logo_pdf_base64'])
                        self.stdout.write(self.style.SUCCESS(f'Logo migrado para agencia: {agencia.nombre} a partir de logo ImageField'))
                        migradas += 1
                        logo_generado = True
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'No se pudo leer logo ImageField de {agencia.nombre}: {e}'))

                # Si no pudo generar desde ImageField, intentar desde logo_base64
                if not logo_generado and agencia.logo_base64 and not agencia.logo_pdf_base64:
                    agencia.logo_pdf_base64 = agencia.logo_base64
                    agencia.save(update_fields=['logo_pdf_base64'])
                    self.stdout.write(self.style.SUCCESS(f'Logo migrado para agencia: {agencia.nombre} a partir de logo_base64'))
                    migradas += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error al migrar agencia {agencia.id}: {e}'))
                errores += 1

        self.stdout.write(self.style.SUCCESS(f'Migración completada. Exitosas: {migradas}. Errores: {errores}.'))

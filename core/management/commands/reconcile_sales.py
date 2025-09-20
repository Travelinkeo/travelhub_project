
import logging
from decimal import Decimal, InvalidOperation

import fitz  # PyMuPDF
from django.core.management.base import BaseCommand, CommandParser

from core.models.boletos import BoletoImportado
from core.report_parser import parse_travelinkeo_report_with_gemini

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Reconcilia un reporte de ventas de Travelinkeo con los boletos en la base de datos.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('report_path', type=str, help='La ruta absoluta al archivo PDF del reporte.')

    def handle(self, *args, **options):
        report_path = options['report_path']
        self.stdout.write(self.style.SUCCESS(f'Iniciando conciliación para el reporte: {report_path}'))

        try:
            # 1. Extraer texto del PDF usando PyMuPDF
            self.stdout.write("Paso 1: Extrayendo texto del archivo PDF...")
            ocr_text = ""
            with fitz.open(report_path) as doc:
                for page in doc:
                    ocr_text += page.get_text()
            
            if not ocr_text.strip():
                self.stderr.write(self.style.ERROR("No se pudo extraer texto del PDF. El archivo podría estar vacío o ser una imagen sin OCR."))
                return

            # 2. Parsear el texto extraído con IA
            self.stdout.write("Paso 2: Parseando datos del reporte con IA...")
            parsed_sales = parse_travelinkeo_report_with_gemini(ocr_text)

            if not parsed_sales:
                self.stderr.write(self.style.ERROR("La IA no pudo parsear el reporte. Verifique el log para más detalles."))
                return

            self.stdout.write(self.style.SUCCESS(f'{len(parsed_sales)} registros de ventas parseados con éxito.'))

            # 3. Realizar la conciliación
            self.stdout.write("Paso 3: Realizando conciliación con la base de datos...")
            found_count = 0
            not_found_count = 0
            discrepancy_count = 0

            for sale in parsed_sales:
                ticket_number = sale.get('numero_boleto')
                report_total_str = sale.get('monto_a_pagar')

                if not ticket_number or report_total_str is None:
                    self.stdout.write(self.style.WARNING(f"Registro ignorado en el reporte por falta de datos: {sale}"))
                    continue
                
                try:
                    report_total = Decimal(str(report_total_str))
                except (InvalidOperation, TypeError):
                    self.stdout.write(self.style.WARNING(f"Valor inválido para 'monto_a_pagar' en el reporte para boleto {ticket_number}: {report_total_str}"))
                    continue

                try:
                    boleto_db = BoletoImportado.objects.get(numero_boleto=ticket_number)
                    found_count += 1
                    
                    # Asumimos que el campo en la BD se llama 'total_a_pagar' y es de tipo Decimal
                    db_total = boleto_db.total_a_pagar or Decimal('0.0')

                    if abs(db_total - report_total) > Decimal('0.01'):
                        discrepancy_count += 1
                        self.stdout.write(self.style.WARNING(
                            f"[DISCREPANCIA] Boleto {ticket_number}: Reporte=${report_total:.2f}, Base de Datos=${db_total:.2f}"
                        ))
                    else:
                        self.stdout.write(self.style.SUCCESS(
                            f"[OK] Boleto {ticket_number} conciliado (Monto: {db_total:.2f})"
                        ))

                except BoletoImportado.DoesNotExist:
                    not_found_count += 1
                    self.stdout.write(self.style.ERROR(
                        f"[NO ENCONTRADO] Boleto {ticket_number} del reporte no existe en la base de datos."
                    ))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Error inesperado procesando boleto {ticket_number}: {e}'))
            
            # 4. Imprimir resumen final
            self.stdout.write("\n" + "-"*50)
            self.stdout.write(self.style.SUCCESS('Conciliación Finalizada. Resumen:'))
            self.stdout.write(f"- Registros en el reporte: {len(parsed_sales)}")
            self.stdout.write(self.style.SUCCESS(f"- Boletos encontrados y conciliados: {found_count}"))
            self.stdout.write(self.style.ERROR(f"- Boletos no encontrados en la BD: {not_found_count}"))
            self.stdout.write(self.style.WARNING(f"- Boletos con discrepancias de monto: {discrepancy_count}"))
            self.stdout.write("-"*50)

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"El archivo no fue encontrado en la ruta: {report_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocurrió un error inesperado durante la conciliación: {e}'))


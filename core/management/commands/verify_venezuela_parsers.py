from django.core.management.base import BaseCommand
import os
import sys

# Ensure project root is in path
sys.path.append(r'c:\Users\ARMANDO\travelhub_project')

from core.parsers.web_receipt_parser import WebReceiptParser

class Command(BaseCommand):
    help = 'Proba los parsers de aerolineas venezolanas'

    def handle(self, *args, **options):
        base_path = r'c:\Users\ARMANDO\travelhub_project\core\tests\fixtures\venezuela_web'
import email
from email import policy
from core.ticket_parser import generate_ticket
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from PyPDF2 import PdfReader

class Command(BaseCommand):
    help = 'Proba los parsers de aerolineas venezolanas y genera PDF'

    def handle(self, *args, **options):
        base_path = r'c:\Users\ARMANDO\travelhub_project\core\tests\fixtures\venezuela_web'
        # Lista ampliada de archivos a probar
        files = [
            'rutaca_sample.pdf', 
            'rutaca_sample.eml',
            'avior_sample.pdf', 
            'avior_sample_2.eml',
            'avior_sample.eml',
            'avior_sample_3.eml',
        ]

        parser = WebReceiptParser()

        self.stdout.write(self.style.WARNING(f"Iniciando pruebas de WebReceiptParser en: {base_path}"))

        for f_name in files:
            path = os.path.join(base_path, f_name)
            self.stdout.write(self.style.SUCCESS(f"\n--- Probando archivo: {f_name} ---"))
            
            if not os.path.exists(path):
                self.stdout.write(self.style.ERROR("  [!] Archivo no encontrado - Saltando"))
                continue

            # 1. Obtener contenido (HTML o EML o PDF)
            content = ""
            if f_name.endswith('.eml'):
                with open(path, 'rb') as f:
                    msg = email.message_from_binary_file(f, policy=policy.default)
                    # Buscar parte HTML
                    body = msg.get_body(preferencelist=('html'))
                    if body:
                        content = body.get_content()
                    else:
                        self.stdout.write(self.style.ERROR("  [!] No se encontró parte HTML en el EML"))
                        continue
            elif f_name.endswith('.pdf'):
                try:
                    reader = PdfReader(path)
                    content = ""
                    for page in reader.pages:
                        content += page.extract_text() + "\n"
                except Exception as e:
                     self.stdout.write(self.style.ERROR(f"  [X] Error leyendo PDF: {e}"))
                     continue
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

            # 2. Parsear
            result = parser.parse(content)
            
            if result.get('error'):
                self.stdout.write(self.style.ERROR(f"  [X] ERROR: {result['error']}"))
            else:
                tickets = result.get('tickets', [])
                self.stdout.write(self.style.WARNING(f"  [!] Multi-Pax Mode: {result.get('is_multi_pax')}"))
                self.stdout.write(f"  [i] Total Tickets Generados: {len(tickets)}")
                
                for i, t in enumerate(tickets):
                    self.stdout.write(f"      > Ticket: {t.get('NUMERO_DE_BOLETO')}")
                    self.stdout.write(f"        Pasajero: {t.get('NOMBRE_DEL_PASAJERO')}")
                    self.stdout.write(f"        Saludo: {t.get('SOLO_NOMBRE_PASAJERO')}")
                    self.stdout.write(f"        PNR: {t.get('CODIGO_RESERVA')}")
                    self.stdout.write(f"        Monto: {t.get('TOTAL_MONEDA')} {t.get('TOTAL_IMPORTE')}")
                    
                    for v in t.get('vuelos', []):
                         self.stdout.write(f"           - {v.get('origen')} > {v.get('destino')} ({v.get('fecha')} {v.get('hora_salida')})")
                    
                    # --- INTERACTIVE MANUAL ENTRY ---
                    # Si el ID esta PENDIENTE (Común en Web/PDF), pedirlo manualmente
                    if t.get('CODIGO_IDENTIFICACION') == 'PENDIENTE':
                        self.stdout.write(self.style.WARNING(f"\n  [!] FALTA IDENTIFICACIÓN PARA: {t.get('NOMBRE_DEL_PASAJERO')}"))
                        try:
                            # Python standard input
                            manual_id = input(f"      > Ingrese V/E-Cedula o Pasaporte: ").strip()
                            if manual_id:
                                t['CODIGO_IDENTIFICACION'] = manual_id.upper()
                                self.stdout.write(self.style.SUCCESS(f"      [OK] ID Actualizado a: {t['CODIGO_IDENTIFICACION']}"))
                        except Exception as e:
                            pass # En entornos no interactivos
                    # -------------------------------

                    # 3. Generar PDF para TODOS los tickets
                    try:
                        pdf_content, filename = generate_ticket(t)
                        clean_name = f"output_{t.get('NUMERO_DE_BOLETO')}.pdf"
                        out_path = os.path.join(r'c:\Users\ARMANDO\travelhub_project', clean_name)
                        with open(out_path, 'wb') as pdf_file:
                            pdf_file.write(pdf_content)
                        self.stdout.write(self.style.SUCCESS(f"        [PDF GENERADO]: {out_path}"))
                    except Exception as e:
                            self.stdout.write(self.style.ERROR(f"        [PDF ERROR]: {e}"))
                    
                    self.stdout.write("      -------------------------")

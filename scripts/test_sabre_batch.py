import os
import sys
import json
import django
from decimal import Decimal

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError

def run_test():
    # Lista explícita de archivos proporcionada por el usuario
    # Caso específico reportado como fallido
    files = [
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 27 mayo para NAIDALY DEL CARMEN COHEN CABELLO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 27 mayo para JOSE ARMANDO ALEMAN MARICHALES.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 19 marzo para ROSANGELA DIAZ SILVA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 18 marzo para ROSANGELA DIAZ SILVA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 07 abril para CARLOS MARIO GOMEZ ZULUAGA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 07 abril para ALEXANDER CASTANO VALENCIA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 07 abril para JOHN JAIRO CASTANO VALENCIA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 07 abril para JHONY ALBERTO QUINTERO RAMIREZ.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 29 abril para MARIA FERNANDA HERNANDEZ OCHOA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 29 abril para JORGE HUMBERTO QUICENO GIRALDO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 24 mayo para MAURICIO ISAZA ORTIZ.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 22 mayo para MAURICIO ISAZA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 21 mayo para ANNE MARIE BELLO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 21 mayo para VALERIA VELEZ.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 17 julio para YENY PAOLA AGUILAR ROJAS.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 17 agosto para JIMMY ALEJANDRO ZULUAGA JABER.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 17 agosto para JUAN ELIAS ZULUAGA JABER.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 29 septiembre para JUAN CARLOS VELEZ.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Electronic ticket receipt, October 02 for HECTOR FABIO HOYOS VELARDE.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 04 octubre para MARIA JOSE SISSO VIDAL.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Electronic ticket receipt, November 27 for BETLANA KELY MATA MONTANO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 22 diciembre para ANDY DAVID FARIAS APARCEDO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 03 diciembre para JORGE HUMBERTO QUICENO GIRALDO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, febrero 09 para VARGAS CAMACHO LILIANA ANDREA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo_de_pasaje_electrónico_07_abril_para_ALEXANDER_CASTANO_VALENCIA_AO8QaIN.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo_de_pasaje_electrónico_07_abril_para_ALEXANDER_CASTANO_VALENCIA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 21 diciembre para LAURA CRISTINA ARROYAVE.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 13 febrero para OSCAR DUQUE.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 19 noviembre para ALIKY DE SOUSA.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 29 enero para MATEO ZULUAGA CASTANO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\MBYRDI - GIRALDO CASTANO JUAN CAMILO _ Sabre Red Web.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 17 febrero para IVAN ROSERO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 15 febrero para IVAN ROSERO.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 04 febrero para MR JAIRO DE JESUS SALAZAR SALAZAR.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 04 febrero para MR JOSE LUIS SOTO HERNANDEZ.pdf",
        r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 04 febrero para MR KEVIN EDUARDO QUINTERO RAMOS.pdf",
        r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 09 febrero para JUAN CAMILO GIRALDO CASTANO.pdf"
    ]

    parser = SabreParser()
    results = []

    print(f"--- INICIANDO TEST BATCH SABRE ({len(files)} Archivos) ---\n")

    for file_path in files:
        if not os.path.exists(file_path):
            print(f"❌ ARCHIVO NO ENCONTRADO: {file_path}")
            continue

        try:
            print(f"📂 Procesando: {os.path.basename(file_path)}")
            # Usar extract_data_from_file (método público) o parse (privado)
            # SabreParser por defecto usa parse(text).
            # Debemos extraer texto primero.
            
            import pdfplumber
            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
            
            data_obj = parser.parse(full_text)
            data = data_obj.to_dict()
            
            # Construir estructura para Template
            # La estructura "data" retornada por SabreParser ya debe ser bastante completa.
            # Mapeamos a las variables del template:
            
            template_context = {
                "solo_nombre_pasajero": data.get("solo_nombre_pasajero", "Cliente"),
                "pasajero": {
                    "nombre_completo": data.get("passenger_name") or data.get("passenger", {}).get("name"),
                    "documento_identidad": data.get("passenger_document") or data.get("passenger", {}).get("customerNumber"), # Ajustar segun key real
                },
                "reserva": {
                    "codigo_reservacion": data.get("pnr"),
                    "numero_boleto": data.get("ticket_number"),
                    "fecha_emision": data.get("issue_date") or data.get("reserva", {}).get("fecha_emision"),
                    "aerolinea_emisora": data.get("reserva", {}).get("aerolinea_emisora") or data.get("issuing_airline"),
                    "agente_emisor": {
                        "nombre": data.get("reserva", {}).get("agente_emisor", {}).get("nombre"),
                        "numero_iata": data.get("reserva", {}).get("agente_emisor", {}).get("numero_iata") or data.get("agency_iata")
                    }
                },
                "itinerario": {
                    "vuelos": data.get("flights", [])
                },
                "debug_source_file": os.path.basename(file_path)
            }
            
            results.append(template_context)
            print("✅ Parseo Exitoso")

        except Exception as e:
            print(f"🔥 ERROR parseando {os.path.basename(file_path)}: {e}")

    # Guardar en archivo JSON para inspección visual
    output_path = os.path.join(os.getcwd(), 'SABRE_BATCH_TEST_RESULTS.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, default=decimal_default, ensure_ascii=False)

    print(f"\n--- TEST COMPLETADO ---")
    print(f"Resultados guardados en: {output_path}")

    # GENERACIÓN DE PDFS
    print(f"\n--- GENERANDO PDFS DE EJEMPLO ---")
    output_dir = os.path.join(os.getcwd(), 'sample_pdfs')
    os.makedirs(output_dir, exist_ok=True)

    try:
        from jinja2 import Environment, FileSystemLoader
        from weasyprint import HTML
    except ImportError as e:
        print(f"❌ Falta dependencia (jinja2 o weasyprint): {e}")
        return

    # Configurar Jinja2
    template_dir = os.path.join(os.getcwd(), 'core', 'templates', 'core', 'tickets')
    env = Environment(loader=FileSystemLoader(template_dir))

    for i, res in enumerate(results):
        try:
            # Seleccionar template
            template_name = 'ticket_template_sabre.html'
            template = env.get_template(template_name)
            
            # Renderizar HTML
            html_string = template.render(res)
            
            # Generar PDF
            filename = f"SABRE_SAMPLE_{i+1}_{res['reserva']['aerolinea_emisora']}_{res['solo_nombre_pasajero']}.pdf".replace(' ', '_').replace('/', '-')
            pdf_path = os.path.join(output_dir, filename)
            
            HTML(string=html_string, base_url=os.getcwd()).write_pdf(pdf_path)
            print(f"✅ PDF Generado: {filename}")
            
        except Exception as e:
            print(f"🔥 Error generando PDF {i+1}: {e}")

if __name__ == '__main__':
    run_test()

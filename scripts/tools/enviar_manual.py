
import os
import resend
from weasyprint import HTML, CSS
from dotenv import load_dotenv
import base64

load_dotenv()

# Configuración de Resend
resend.api_key = os.getenv("RESEND_API_KEY")

def generar_y_enviar():
    output_pdf = "c:/Users/ARMANDO/travelhub_project/Manual_TravelHub_2026.pdf"
    
    # Contenido HTML con diseño Premium (Stripe Style)
    html_content = """
    <html>
    <head>
        <style>
            @page { size: A4; margin: 2cm; }
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                line-height: 1.6; 
                color: #333; 
            }
            .header { border-bottom: 2px solid #00D1FF; padding-bottom: 10px; margin-bottom: 30px; }
            h1 { color: #0081C4; font-size: 28pt; margin-bottom: 5pt; }
            h2 { color: #005A8C; border-left: 5px solid #00D1FF; padding-left: 10px; margin-top: 25pt; }
            h3 { color: #555; font-style: italic; }
            .quick-start { background-color: #f0f9ff; border: 1px solid #bae6fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .badge { background: #00D1FF; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
            .ia-tag { color: #8b5cf6; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f8fafc; }
            .footer { position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 9pt; color: #999; border-top: 1px solid #eee; padding-top: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>TravelHub</h1>
            <p>Manual Maestro de Operaciones & Estrategia 2026</p>
        </div>

        <h2>📖 LA HISTORIA DE SOFÍA: Dominando la IA</h2>
        <p>Sofía entró a TravelHub sin saber nada. Hoy, es la mejor asesora. Este manual es su secreto.</p>

        <div class="quick-start">
            <h3>🚀 QUICK START: Tu primera venta en 15 min</h3>
            <ol>
                <li><strong>Registro:</strong> Crea al cliente en CRM > Clientes.</li>
                <li><strong>IA Magic ✨:</strong> Usa el Cotizador Mágico para buscar vuelos en segundos.</li>
                <li><strong>Cierre:</strong> Envía el portal público con el link dinámico de WhatsApp.</li>
            </ol>
        </div>

        <h2>🔄 EL FLUJO DEL ÉXITO (End-to-End)</h2>
        <p>Lead &rarr; Cotización &rarr; Venta &rarr; Boletos &rarr; Factura &rarr; Pago &rarr; Rentabilidad.</p>
        
        <h2>🤖 INTELIGENCIA ARTIFICIAL: Tu Ventaja Competitiva</h2>
        <p>TravelHub identifica boletos de Sabre y KIU automáticamente <span class="badge">LIVE</span>. No más errores de digitación.</p>

        <h2>📊 GUÍA POR ROLES</h2>
        <ul>
            <li><strong>Asesor:</strong> Enfoque en ventas y atención rápida vía Mobile.</li>
            <li><strong>Gerente:</strong> Supervisión de márgenes y ahorro de tiempo.</li>
            <li><strong>Contador:</strong> Conciliación automática y reportes BCV/IGTF.</li>
        </ul>

        <div class="footer">
            Generado automáticamente por TravelHub AI Agent | 2026 | travelhub.cc
        </div>
    </body>
    </html>
    """
    
    print("Generando PDF...")
    HTML(string=html_content).write_pdf(output_pdf)
    print(f"PDF generado: {output_pdf}")

    # Leer el PDF para adjuntarlo
    with open(output_pdf, "rb") as f:
        pdf_content = f.read()
        attachment = base64.b64encode(pdf_content).decode()

    # Enviar Email
    print("Enviando email vía Resend...")
    params = {
        "from": "TravelHub <notificaciones@travelhub.cc>",
        "to": ["travelinkeo@gmail.com"], # Nueva dirección principal
        "subject": "📄 Tu Manual Maestro de TravelHub (Edición 2026)",
        "html": "<p>Hola Armando,<br><br>Adjunto encontrarás el nuevo <strong>Manual Maestro de TravelHub 2026</strong> reestructurado y optimizado con las últimas funciones de IA.<br><br>¡Éxito con esas ventas!<br><br>TravelHub AI Agent</p>",
        "attachments": [
            {
                "content": attachment,
                "filename": "Manual_TravelHub_2026.pdf",
            }
        ],
    }

    email = resend.Emails.send(params)
    print(f"Email enviado con éxito. ID: {email['id']}")

if __name__ == "__main__":
    generar_y_enviar()

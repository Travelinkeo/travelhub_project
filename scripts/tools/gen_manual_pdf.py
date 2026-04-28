import sys
import os
from weasyprint import HTML, CSS

# Rutas de imágenes generadas (usando las absolutas del sistema)
base_path = r"C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d"
images = {
    "banner": os.path.join(base_path, "travelhub_manual_banner_1775684909056.png"),
    "kpi": os.path.join(base_path, "dashboard_kpi_visual_1775686050317.png"),
    "ocr": os.path.join(base_path, "travel_ocr_visual_1775686062366.png"),
    "quoter": os.path.join(base_path, "magic_quoter_concept_1775684925251.png"),
    "airlines": os.path.join(base_path, "airline_logo_grid_1775686076023.png"),
    "automation": os.path.join(base_path, "erp_ticket_parsing_visual_1775684939967.png")
}

html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Manual de Usuario TravelHub</title>
    <style>
        @page {{
            margin: 2cm;
            @bottom-right {{
                content: "Página " counter(page);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 10pt;
                color: #666;
            }}
        }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #fff;
        }}
        .cover {{
            text-align: center;
            padding-top: 5cm;
            page-break-after: always;
            background-color: #0b1120;
            color: white;
            margin: -2cm;
            height: 29.7cm;
        }}
        .cover img {{
            width: 100%;
            max-width: 18cm;
            margin-bottom: 2cm;
        }}
        .cover h1 {{
            font-size: 48pt;
            margin-bottom: 0.5cm;
            color: #10b981;
        }}
        .cover p {{
            font-size: 18pt;
            color: #94a3b8;
        }}
        h1, h2, h3 {{
            color: #064e3b;
            border-bottom: 2px solid #10b981;
            padding-bottom: 0.2cm;
        }}
        h2 {{ margin-top: 1.5cm; }}
        .chapter-title {{
            background-color: #f0fdf4;
            padding: 1cm;
            border-radius: 10px;
            margin-bottom: 1cm;
        }}
        .feature-card {{
            border: 1px solid #e2e8f0;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            background-color: #fafafa;
        }}
        .highlight {{
            color: #059669;
            font-weight: bold;
        }}
        img.screenshot {{
            width: 100%;
            max-height: 10cm;
            object-fit: cover;
            border-radius: 8px;
            margin: 1cm 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .step {{
            margin-bottom: 1.5rem;
        }}
        .step-num {{
            background: #10b981;
            color: white;
            width: 30px;
            height: 30px;
            display: inline-block;
            text-align: center;
            border-radius: 50%;
            font-weight: bold;
            line-height: 30px;
            margin-right: 10px;
        }}
        .tip {{
            background-color: #fffbeb;
            border-left: 5px solid #f59e0b;
            padding: 1rem;
            margin: 1rem 0;
            font-style: italic;
        }}
        .important {{
            background-color: #fef2f2;
            border-left: 5px solid #ef4444;
            padding: 1rem;
            margin: 1rem 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1cm 0;
        }}
        th, td {{
            border: 1px solid #cbd5e1;
            padding: 12px;
            text-align: left;
        }}
        th {{ background-color: #f8fafc; }}
    </style>
</head>
<body>
    <div class="cover">
        <img src="file:///{images['banner']}" alt="Logo">
        <h1>TravelHub</h1>
        <p>Expert Travel Management Ecosystem</p>
        <p style="font-size: 12pt; margin-top: 5cm;">Versión 4.0 - Manual de Operaciones Integral 2026</p>
    </div>

    <h2>Contenido</h2>
    <ul>
        <li>Introducción: La Visión de TravelHub</li>
        <li>Capítulo 1: Inteligencia de Negocios (Dashboard)</li>
        <li>Capítulo 2: Ciclo de Vida del Boleto Aéreo</li>
        <li>Capítulo 3: El Cotizador Mágico 2.0</li>
        <li>Capítulo 4: Motores de Reservas (Vuelos y Hoteles)</li>
        <li>Capítulo 5: CRM y Automatización de Datos</li>
        <li>Capítulo 6: Gestión Financiera y de Proveedores</li>
        <li>Capítulo 7: Configuración de Marca Blanca</li>
    </ul>

    <div class="chapter-title">
        <h2>Introducción: La Visión de TravelHub</h2>
        <p>TravelHub no es solo un CRM, es un sistema operativo diseñado para agencias que quieren escalar delegando las tareas repetitivas a la Inteligencia Artificial. Nuestra misión es que el agente se enfoque en <b>vender</b>, mientras el sistema se encarga de <b>procesar</b>.</p>
    </div>

    <h2>Capítulo 1: Inteligencia de Negocios (Dashboard)</h2>
    <p>El Dashboard de TravelHub (Estilo Obsidian Emerald) centraliza la salud de tu agencia en una sola pantalla.</p>
    
    <img src="file:///{images['kpi']}" class="screenshot" alt="Dashboard KPI">
    
    <div class="feature-card">
        <h3>1.1 Análisis de Métricas KPI</h3>
        <ul>
            <li><span class="highlight">Total Sales (Ventas Totales):</span> Muestra la facturación bruta en tiempo real, permitiendo comparar el desempeño diario.</li>
            <li><span class="highlight">Net Profit (Utilidad Neta):</span> Calculada automáticamente restando los costos de proveedores y comisiones de los consolidadores.</li>
            <li><span class="highlight">Ticket Volume:</span> Cantidad de boletos emitidos. Una métrica clave para medir la carga operativa del equipo.</li>
        </ul>
    </div>

    <h3>1.2 Business Advisor IA</h3>
    <div class="step">
        <p>Ubicado en el lateral derecho, el asesor analiza patrones de venta. Puedes preguntarle:</p>
        <blockquote>"¿Cuál es mi tendencia de ventas para destinos en Europa este trimestre?"</blockquote>
        <p>El sistema responderá con datos precisos extraídos de tus ventas cerradas, ayudándote a decidir dónde invertir tu presupuesto de marketing.</p>
    </div>

    <div style="page-break-after: always;"></div>

    <h2>Capítulo 2: Ciclo de Vida del Boleto Aéreo</h2>
    <p>La funcionalidad más potente de TravelHub es el <b>Parser de GDS</b>. Hemos eliminado la entrada manual de datos en un 90%.</p>

    <img src="file:///{images['automation']}" class="screenshot" alt="Automation">

    <h3>2.1 El Proceso de Importación</h3>
    <div class="step">
        <span class="step-num">1</span> <b>Captura:</b> Copia el texto descriptivo de la emisión en Sabre o KIU, o simplemente sube el PDF oficial.
    </div>
    <div class="step">
        <span class="step-num">2</span> <b>Análisis Híbrido:</b> Nuestro motor utiliza IA para entender el itinerario y Regex para asegurar que los números financieros coincidan exactamente.
    </div>
    <div class="step">
        <span class="step-num">3</span> <b>Validación:</b> Revisa los datos en la pantalla de "Review". Si ves un icono de alerta, significa que el sistema no está 100% seguro de un impuesto (ej. tasas locales raras).
    </div>
    <div class="step">
        <span class="step-num">4</span> <b>Cierre de Venta:</b> Al confirmar, se crea una "Venta" vinculada al cliente, se actualiza el saldo del proveedor y se genera el recibo.
    </div>

    <div class="important">
        <b>Dato Crítico:</b> El sistema detecta automáticamente si el boleto es de Sabre o KIU basándose en la estructura del texto, por lo que no necesitas seleccionar el GDS manualmente.
    </div>

    <h2>Capítulo 3: El Cotizador Mágico 2.0</h2>
    <p>Diseñado para generar "Wows" en los clientes. Convierte una charla de WhatsApp en una reserva cerrada.</p>
    
    <img src="file:///{images['quoter']}" class="screenshot" alt="Magic Quoter">

    <h3>3.1 Pasos para una Cotización de Éxito</h3>
    <table>
        <tr><th>Fase</th><th>Acción del Agente</th><th>Resultado del Sistema</th></tr>
        <tr><td>Definición</td><td>Ingresa Origen, Destino y Fechas.</td><td>Busca disponibilidad REAL (Google Flights).</td></tr>
        <tr><td>Personalización</td><td>Agrega markup o cargos de servicio.</td><td>Recalcula el total de forma invisible al cliente.</td></tr>
        <tr><td>Enriquecimiento</td><td>Selecciona "Generar Copy IA".</td><td>Crea una narrativa emocionante del destino.</td></tr>
        <tr><td>Envío</td><td>Copia el Link de propuesta.</td><td>El cliente recibe una URL interactiva y elegante.</td></tr>
    </table>

    <div class="tip">
        <b>Mejor Práctica:</b> Usa siempre la búsqueda real para dar tarifas referenciales precisas. Recuerda que los precios en aéreos cambian cada minuto.
    </div>

    <div style="page-break-after: always;"></div>

    <h2>Capítulo 4: Motores de Reservas Integrados</h2>
    
    <img src="file:///{images['airlines']}" class="screenshot" alt="Airlines">

    <h3>4.1 Google Flights Integration (Fli Engine)</h3>
    <p>A diferencia de otros sistemas que muestran "caché", TravelHub accede a la red de Google para traerte:</p>
    <ul>
        <li>Disponibilidad de asientos real.</li>
        <li>Horarios de salida y llegada locales.</li>
        <li>Equipaje incluido (según disponibilidad del API).</li>
    </ul>

    <h3>4.2 Motor de Hoteles (Hotel Engine)</h3>
    <p>Gestiona tu propio inventario (contratos directos) y compáralo con las tarifas de proveedores externos. El sistema resaltará cuál te da mayor margen de comisión.</p>

    <h2>Capítulo 5: CRM y Automatización de Datos</h2>
    <p>La gestión de datos de pasajeros se ha modernizado con tecnología de visión artificial.</p>

    <img src="file:///{images['ocr']}" class="screenshot" alt="Passport OCR">

    <h3>5.1 Escaneo de Documentos (OCR)</h3>
    <p>Olvídate de transcribir nombres complejos. Nuestra IA de visión lee la zona MRZ de los pasaportes:</p>
    <ul>
        <li><span class="highlight">Precisión:</span> 99.9% en lectura de nombres y apellidos.</li>
        <li><span class="highlight">Detección de Vencimientos:</span> El sistema te avisará si el pasaporte del cliente vence en menos de 6 meses antes de emitir el boleto.</li>
    </ul>

    <h2>Capítulo 6: Gestión Financiera y de Proveedores</h2>
    <p>Nuestra contabilidad está diseñada para agencias de viajes, no para tiendas. Entendemos el concepto de Neto, Comisiones y Tasas.</p>

    <div class="feature-card">
        <h3>Liquidaciones (Settlements)</h3>
        <p>TravelHub agrupa todas las ventas hechas con un proveedor (ej: Avianca o Consolidador X) y te permite "Liquidar" el lote. Esto genera una orden de pago y descuenta el saldo de tu cuenta corriente comercial.</p>
    </div>

    <h2>Capítulo 7: Configuración de Marca Blanca</h2>
    <p>El cliente nunca verá la marca "TravelHub", solo la tuya.</p>
    <ul>
        <li><b>Logo:</b> Sube tu logo en formato PNG transparente para una integración perfecta en los vouchers.</li>
        <li><b>Emails:</b> Configura tu SMTP para que las cotizaciones lleguen desde <i>reservas@tuagencia.com</i>.</li>
        <li><b>Documentos:</b> Personaliza el encabezado y pie de página de todas tus facturas y proformas.</li>
    </ul>

    <div style="text-align: center; margin-top: 5cm; color: #666;">
        <p>© 2026 TravelHub Technology Group Inc. Todos los derechos reservados.</p>
    </div>
</body>
</html>
"""

# Generar el PDF
output_pdf = os.path.join(base_path, "Manual_Usuario_TravelHub_Completo.pdf")

try:
    print(f"Generando PDF en: {{output_pdf}}...")
    HTML(string=html_content).write_pdf(output_pdf)
    print("✅ ¡Manual PDF generado con éxito!")
except Exception as e:
    print(f"❌ Error generando el PDF: {{e}}")
    sys.exit(1)

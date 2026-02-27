import os
import django
import sys
import json

sys.path.append(r"C:\Users\ARMANDO\travelhub_project")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.wiki import WikiArticulo

titulo = "Documentación SaaS Mailbot (Automatización)"
contenido = """
<h3>¿Qué es y cuál es su alcance?</h3>
<p>Es un robot autónomo que vive en tu servidor y trabaja 24/7. Su misión es eliminar la carga manual de "subir boletos" al sistema.</p>
<h4>Alcance Actual:</h4>
<ul>
    <li><strong>Lee:</strong> Tu correo <code>viajes.travelinkeo@gmail.com</code>.</li>
    <li><strong>Procesa:</strong> Boletos de Sabre, Amadeus, Kiu, Copa, Rutaca, Estelar, Avior, etc.</li>
    <li><strong>Entiende:</strong> Tanto el texto del correo (HTML) como los adjuntos (PDFs).</li>
    <li><strong>Acción:</strong>
        <ol>
            <li>Crea la venta en el sistema automáticamente.</li>
            <li>Genera un PDF unificado con tu marca (TravelHub).</li>
            <li>Te avisa si algo salió mal.</li>
        </ol>
    </li>
</ul>

<h3>¿Cómo funciona por dentro? (Flujo Técnico)</h3>
<ol>
    <li><strong>El Ojo (IMAP):</strong> El bot "escucha" tu bandeja de entrada. Cada 60 segundos busca correos no leídos con palabras clave como "Ticket", "Itinerary", "Reserva", "Copa", "Rutaca".</li>
    <li><strong>El Cerebro (Gemini AI + Regex):</strong> Cuando encuentra un correo, extrae el texto y los adjuntos. Se lo envía a <strong>Google Gemini Pro (IA)</strong> con instrucciones precisas para que "entienda" dónde está el número de boleto, el pasajero y el itinerario, sin importar qué tan desordenado esté el formato original.</li>
    <li><strong>El Motor (Django):</strong> Guarda la información en tu base de datos (<code>BoletoImportado</code>). Si detecta que el pasajero ya existe, lo asocia. Si no, crea los datos necesarios.</li>
    <li><strong>La Imprenta (WeasyPrint):</strong> Toma los datos limpios y los "imprime" en tu plantilla HTML (<code>ticket_template_kiu_bolivares.html</code>), creando un PDF limpio y profesional.</li>
    <li><strong>El Archivo (Google Drive):</strong> Sube automáticamente ese PDF nuevo a tu carpeta de Google Drive <code>Travelinkeo/Boletos</code> (si está configurado).</li>
</ol>

<h3>Herramientas que intervienen:</h3>
<ul>
    <li><strong>Python/Django:</strong> El corazón del sistema.</li>
    <li><strong>Google Gemini Pro:</strong> La inteligencia que descifra los boletos difíciles.</li>
    <li><strong>IMAP (Gmail):</strong> Para leer los correos.</li>
    <li><strong>WeasyPrint:</strong> Para generar los PDFs.</li>
</ul>
"""

tags = ["MAILBOT", "SAAS", "AUTOMATIZACION", "SOPORTE", "AYUDA"]

obj, created = WikiArticulo.objects.get_or_create(
    titulo=titulo,
    defaults={
        'contenido': contenido,
        'tags': tags,
        'categoria': 'GENERAL',
        'activo': True
    }
)

if not created:
    obj.contenido = contenido
    obj.tags = tags
    obj.save()
    print("Documentación actualizada.")
else:
    print("Documentación creada.")

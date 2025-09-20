import json
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.gemini import generate_content
from core.models.ventas import Venta

# --- Funciones Auxiliares (Simuladas y Reales) ---

def _get_weather_forecast(city_name: str) -> dict:
    """
    SIMULACIÓN: Llama a una API externa de clima.
    En una implementación real, aquí usarías una librería como `requests`
    para llamar a un servicio como OpenWeatherMap, WeatherAPI, etc.
    """
    print(f"Simulando obtención de clima para: {city_name}")
    # Datos de ejemplo para la simulación
    if "cancún" in city_name.lower():
        return {"temp_celsius": 28, "condition": "Parcialmente nublado con probabilidad de chubascos", "icon": "🌦️"}
    elif "madrid" in city_name.lower():
        return {"temp_celsius": 32, "condition": "Despejado y soleado", "icon": "☀️"}
    else:
        return {"temp_celsius": 25, "condition": "Agradable", "icon": "😊"}

def _generate_reminder_email_content(venta: Venta, weather_forecast: dict) -> dict:
    """
    Prepara y envía el prompt a Gemini para generar el contenido del email.
    """
    cliente = venta.cliente
    primer_vuelo = venta.segmentos_vuelo.order_by('fecha_salida').first()
    
    if not primer_vuelo:
        return None

    # Formatear los detalles del vuelo para el prompt
    flight_details = []
    for s in venta.segmentos_vuelo.all():
        flight_details.append(
            f"- Vuelo {s.aerolinea} {s.numero_vuelo} de {s.origen.nombre} a {s.destino.nombre}. "
            f"Sale: {s.fecha_salida.strftime('%d/%m/%Y a las %H:%M')}, "
            f"Llega: {s.fecha_llegada.strftime('%d/%m/%Y a las %H:%M')}."
        )
    itinerary_str = "\n".join(flight_details)

    # --- Prompt para Gemini ---
    prompt = f"""
    Eres 'TravelBot', el asistente virtual amigable y servicial de la agencia de viajes TravelHub.
    Tu tarea es redactar un email de recordatorio de viaje para un cliente.

    **Contexto:**
    El viaje del cliente está a punto de comenzar. Queremos enviarle un recordatorio útil y emocionante,
    y al mismo tiempo, sugerirle un servicio adicional que podría necesitar.

    **Datos para el Email:**
    - **Nombre del Cliente:** {cliente.nombres} {cliente.apellidos}
    - **Código de Reserva (PNR):** {venta.localizador}
    - **Itinerario de Vuelo:**
    {itinerary_str}
    - **Pronóstico del Tiempo para el Destino ({primer_vuelo.destino.nombre}):**
      - Temperatura: {weather_forecast.get('temp_celsius')}°C
      - Condición: {weather_forecast.get('condition')}

    **Instrucciones para la Redacción:**
    1.  **Asunto:** Crea un asunto de email corto, emocionante y personalizado.
    2.  **Cuerpo del Email:**
        - Saluda al cliente por su nombre de forma cálida.
        - Recuérdale que su viaje está cerca y muéstrate emocionado por él.
        - Confirma sutilmente los detalles del primer vuelo.
        - Menciona el pronóstico del tiempo y dale un consejo útil relacionado (ej: "¡No olvides el protector solar!" o "Una chaqueta ligera será tu mejor aliada para las noches.").
        - De forma natural, realiza una venta cruzada sugiriendo reservar un traslado desde el aeropuerto para una llegada sin estrés. Menciona que pueden contactar a la agencia para añadirlo.
        - Despídete cordialmente en nombre de TravelHub.
    3.  **Formato de Salida:** Tu respuesta DEBE ser un único objeto JSON válido con dos claves: `subject` y `body`.

    **Ejemplo de Salida JSON:**
    {{
        "subject": "¡Tu aventura en {primer_vuelo.destino.nombre} está a punto de comenzar, {cliente.nombres}! ✈️",
        "body": "Hola {cliente.nombres},..."
    }}
    """

    try:
        response_text = generate_content(prompt)
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        return json.loads(response_text)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error al generar contenido con Gemini: {e}")
        return None

# --- Clase del Comando de Django ---

class Command(BaseCommand):
    help = 'Envía recordatorios de viaje a clientes con viajes próximos en los siguientes 3 días.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando tarea de envío de recordatorios de viaje..."))

        # 1. Obtener todas las ventas cuyo viaje comience en los próximos 3 días
        today = timezone.now()
        three_days_from_now = today + timedelta(days=3)

        # Buscamos ventas confirmadas que tengan al menos un segmento de vuelo en la ventana de 3 días
        upcoming_ventas = Venta.objects.filter(
            estado=Venta.EstadoVenta.CONFIRMADA,
            segmentos_vuelo__fecha_salida__range=(today, three_days_from_now)
        ).distinct()

        if not upcoming_ventas.exists():
            self.stdout.write(self.style.SUCCESS("No hay viajes próximos para notificar hoy."))
            return

        self.stdout.write(f"Se encontraron {upcoming_ventas.count()} ventas con viajes próximos.")

        # 2. Iterar sobre las ventas y procesar cada una
        for venta in upcoming_ventas:
            self.stdout.write(f"Procesando recordatorio para la venta PNR: {venta.localizador}...")
            cliente = venta.cliente
            primer_vuelo = venta.segmentos_vuelo.order_by('fecha_salida').first()

            if not primer_vuelo:
                self.stderr.write(self.style.WARNING(f"  - La venta {venta.localizador} no tiene segmentos de vuelo. Saltando."))
                continue

            # 3. Obtener el pronóstico del tiempo (simulado)
            destino_ciudad = primer_vuelo.destino.nombre
            weather_data = _get_weather_forecast(destino_ciudad)

            # 4. Generar el contenido del email con Gemini
            email_content = _generate_reminder_email_content(venta, weather_data)

            if not email_content:
                self.stderr.write(self.style.ERROR(f"  - No se pudo generar el contenido del email para {venta.localizador}."))
                continue

            # 5. Enviar el email (implementación real)
            try:
                send_mail(
                    subject=email_content['subject'],
                    message=email_content['body'],
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[cliente.email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f"  - Email de recordatorio enviado a {cliente.email} para la venta {venta.localizador}."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  - Error al enviar email para {venta.localizador}: {e}"))

        self.stdout.write(self.style.SUCCESS("Tarea de envío de recordatorios finalizada."))

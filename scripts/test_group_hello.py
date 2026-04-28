
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.utils.telegram_utils import send_telegram_alert_sync

def test_group_alert():
    print("📢 Enviando saludo al GRUPO...")
    send_telegram_alert_sync(
        "👋 <b>¡Hola Equipo Travelinkeo!</b>\n\n"
        "El bot de TravelHub está conectado a este grupo.\n"
        "Aquí recibirán:\n"
        "✅ Notificaciones de Boletos Nuevos\n"
        "✅ Alertas de Check-in\n"
        "✅ Reportes automáticos"
    )
    print("✅ Mensaje enviado.")

if __name__ == "__main__":
    test_group_alert()


import os
import sys
import asyncio
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.utils.telegram_utils import send_telegram_alert

async def test():
    print("📨 Enviando alerta de prueba a Telegram...")
    success = await send_telegram_alert(
        "🚀 **Prueba de Sistema TravelHub**\n\n"
        "Si lees esto, tu 'Oficina Digital' está lista.\n"
        "Este mensaje fue enviado desde el código de TravelHub sin que tú escribieras nada.\n\n"
        "✅ Reemplazo de Mailbot: ACTIVO"
    )
    
    if success:
        print("✅ Mensaje enviado con éxito.")
    else:
        print("❌ Falló el envío.")

if __name__ == "__main__":
    asyncio.run(test())

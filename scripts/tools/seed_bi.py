import os
import django
import json
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.agencia import Agencia

def seed_insights():
    # Buscamos la primera agencia disponible
    agencia = Agencia.objects.first()
    if not agencia:
        print("❌ No hay agencias en la base de datos.")
        return

    insights = [
        "Tu crecimiento del 15% es sólido. Enfócate en el corredor Europa este mes para maximizar comisiones.",
        "Tienes $3,450 en Tax Refund sin reclamar. Inicia los trámites hoy para inyectar liquidez inmediata.",
        "El segmento de Business Class ha subido. Considera un programa de lealtad para estos 5 clientes clave."
    ]

    agencia.bi_insights = {
        'fecha': timezone.now().isoformat(),
        'consejos': insights,
        'stats_snapshot': {
            'ventas': 125000.00,
            'tax': 3450.00
        }
    }
    agencia.save()
    print(f"✅ AI Insights inyectados para {agencia.nombre}. ¡Dashboard listo!")

if __name__ == '__main__':
    seed_insights()

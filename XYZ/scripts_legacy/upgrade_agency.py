# upgrade_agency.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Agencia

def upgrade():
    print("--- Iniciando Actualización de Agencia ---")
    
    try:
        agencia = Agencia.objects.get(nombre="Travelinkeo")
        print(f"Agencia encontrada: {agencia.nombre} ({agencia.plan})")
        
        # Upgrade to Enterprise
        agencia.plan = 'ENTERPRISE'
        agencia.limite_usuarios = 999999
        agencia.limite_ventas_mes = 999999
        agencia.save()
        
        print("✅ Plan actualizado a ENTERPRISE.")
        print("✅ Límites eliminados (Usuarios/Ventas: 999999).")
        
    except Agencia.DoesNotExist:
        print("❌ Agencia 'Travelinkeo' no encontrada.")

if __name__ == '__main__':
    upgrade()

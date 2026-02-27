# restore_providers.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Proveedor, Agencia

def restore():
    print("--- Iniciando Restauración de Proveedores ---")
    
    # 1. Obtener Agencia Travelinkeo
    try:
        agencia = Agencia.objects.get(nombre="Travelinkeo")
        print(f"✅ Agencia encontrada: {agencia.nombre}")
    except Agencia.DoesNotExist:
        print("❌ Error: Agencia 'Travelinkeo' no encontrada. Ejecute restore_users.py primero.")
        return

    # 2. Lista de Proveedores a restaurar
    # Tipos: 'AER' (Aerolínea), 'CON' (Consolidador), 'OTR' (Otro)
    providers_data = [
        {"nombre": "Estelar", "tipo": "AER", "nivel": "DIR"},
        {"nombre": "Avior", "tipo": "AER", "nivel": "DIR"},
        {"nombre": "Rutaca", "tipo": "AER", "nivel": "DIR"},
        {"nombre": "My Destiny", "tipo": "CON", "nivel": "CON"},
        {"nombre": "Contrataciones Turisticas", "tipo": "CON", "nivel": "CON"},
        {"nombre": "BT Travel", "tipo": "CON", "nivel": "CON"},
    ]

    for p_data in providers_data:
        prov, created = Proveedor.objects.get_or_create(
            nombre=p_data["nombre"],
            defaults={
                "tipo_proveedor": p_data["tipo"],
                "nivel_proveedor": p_data["nivel"],
                "activo": True,
                "agencia": agencia  # Asignamos a la agencia específica
            }
        )
        
        if created:
            print(f"✅ Proveedor '{p_data['nombre']}' restaurado.")
        else:
            print(f"ℹ️ Proveedor '{p_data['nombre']}' ya existía.")
            # Asegurar que esté vinculado a la agencia si estaba huérfano (opcional)
            if not prov.agencia:
                prov.agencia = agencia
                prov.save()
                print(f"   -> Vinculado a {agencia.nombre}")

    print("\n--- Restauración Completada ---")

if __name__ == '__main__':
    restore()

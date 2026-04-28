import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Agencia, UsuarioAgencia, Moneda
from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    admin_user = User.objects.filter(username='admin').first()
    
    if not admin_user:
        print("❌ Error: No se encontró el usuario 'admin'. Por favor, crea un superusuario primero.")
        exit(1)
        
    agencia, created = Agencia.objects.get_or_create(
        nombre='Agencia Central', 
        defaults={'iata': '123456', 'propietario': admin_user}
    )
    if created:
        print(f"✅ Agencia '{agencia.nombre}' creada con éxito.")
    else:
        print(f"ℹ️ Agencia '{agencia.nombre}' ya existía.")
        
    ua, ua_created = UsuarioAgencia.objects.get_or_create(
        usuario=admin_user, 
        agencia=agencia, 
        defaults={'rol': 'admin'}
    )
    if ua_created:
        print(f"✅ Usuario '{admin_user.username}' asignado como ADMIN a la agencia '{agencia.nombre}'.")
    else:
        print(f"ℹ️ Usuario '{admin_user.username}' ya estaba asignado a la agencia '{agencia.nombre}'.")
        
    moneda, mon_created = Moneda.objects.get_or_create(
        codigo_iso='USD', 
        defaults={'nombre': 'Dolar Estadounidense', 'simbolo': '$'}
    )
    if mon_created:
        print(f"✅ Moneda '{moneda.codigo_iso}' creada con éxito.")
    else:
        print(f"ℹ️ Moneda '{moneda.codigo_iso}' ya existía.")
        
    # Activar la agencia actual de admin
    admin_user.agencia_actual_id = agencia.id
    admin_user.save()
    print("✅ Agencia Central configurada como agencia activa para el usuario admin.")
    
    print("🚀 FIN: Script de provisionamiento ejecutado con éxito.")
    
except Exception as e:
    print(f"❌ Error durante el provisionamiento: {e}")


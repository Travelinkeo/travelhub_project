
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from personas.models import Pasajero, Cliente

def encrypt_data():
    print("🔒 Iniciando encriptación final de PII...")
    
    # 1. Pasajeros
    pasajeros = Pasajero.objects.all()
    count_p = 0
    for p in pasajeros:
        if p.numero_documento:
            # Al leer p.numero_documento, obtenemos texto plano (gracias al fallback en to_python/from_db_value)
            # Al guardar, se cifra automáticamente por el campo EncryptedCharField
            p.save() 
            count_p += 1
    print(f"✅ Pasajeros encriptados: {count_p}")

    # 2. Clientes
    clientes = Cliente.objects.all()
    count_c = 0
    for c in clientes:
        if c.numero_pasaporte:
            c.save()
            count_c += 1
    print(f"✅ Clientes encriptados: {count_c}")
    
    print("⚠️ IMPORTANTE: Si ves 'gAAAA...' en la base de datos cruda, es correcto.")

if __name__ == '__main__':
    encrypt_data()

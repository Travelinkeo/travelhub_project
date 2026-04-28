
import os
import sys
import django
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from personas.models import Pasajero, Cliente

def get_sha256(text):
    if not text:
        return None
    return hashlib.sha256(text.encode()).hexdigest()

def populate_hashes():
    print("🔐 Iniciando generación de hashes para PII...")
    
    # 1. Pasajeros
    pasajeros = Pasajero.objects.all()
    count_p = 0
    for p in pasajeros:
        if p.numero_documento and not p.numero_documento_hash:
            p.numero_documento_hash = get_sha256(p.numero_documento)
            # Guardamos solo el campo hash para no disparar otras validaciones o señales pesadas si es posible
            # Pero usando save(update_fields) es mas seguro
            p.save(update_fields=['numero_documento_hash'])
            count_p += 1
    print(f"✅ Pasajeros procesados: {count_p}")

    # 2. Clientes
    clientes = Cliente.objects.all()
    count_c = 0
    for c in clientes:
        if c.numero_pasaporte and not c.numero_pasaporte_hash:
            c.numero_pasaporte_hash = get_sha256(c.numero_pasaporte)
            c.save(update_fields=['numero_pasaporte_hash'])
            count_c += 1
    print(f"✅ Clientes procesados: {count_c}")

if __name__ == '__main__':
    populate_hashes()

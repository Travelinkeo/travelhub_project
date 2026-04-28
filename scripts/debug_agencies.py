
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import Agencia, UsuarioAgencia
from apps.bookings.models import BoletoImportado
from django.contrib.auth.models import User

def debug_data():
    print("-" * 50)
    print("DEBUGGING AGENCIES & BOLETOS")
    print("-" * 50)
    
    agencias = Agencia.objects.all()
    print(f"Total Agencias: {agencias.count()}")
    for a in agencias:
        count = BoletoImportado.objects.filter(agencia=a).count()
        print(f" - {a.nombre} (ID {a.pk}): {count} Boletos")
        
    orphans = BoletoImportado.objects.filter(agencia__isnull=True).count()
    print(f" - [ORPHANS/NO AGENCY]: {orphans} Boletos")
    
    print("-" * 50)
    try:
        u = User.objects.get(username='ARMANDO')
        print(f"User: {u.username}")
        print(f"Is Superuser: {u.is_superuser}")
        
        ua = UsuarioAgencia.objects.filter(usuario=u, activo=True).first()
        if ua:
            print(f"Linked Agency: {ua.agencia.nombre} (ID {ua.agencia.pk})")
        else:
            print("Linked Agency: NONE")
            
    except User.DoesNotExist:
        print("User 'ARMANDO' not found.")
    print("-" * 50)

if __name__ == "__main__":
    debug_data()

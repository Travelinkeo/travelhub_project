import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.crm.models import Pasajero

def migrate_docs():
    pasajeros = Pasajero.objects.all()
    count_pass = 0
    count_ci = 0
    count_otro = 0
    
    print(f"Iniciando migración para {pasajeros.count()} pasajeros...")
    
    for p in pasajeros:
        doc = p.numero_documento
        if not doc:
            continue
            
        if p.tipo_documento == 'PASS':
            p.numero_pasaporte = doc
            count_pass += 1
        elif p.tipo_documento == 'CI':
            p.cedula_identidad = doc
            count_ci += 1
        else:
            # Fallback for 'OTRO' -> map it to cedula as it's not a Passport.
            p.cedula_identidad = doc
            count_otro += 1
            
        p.save(update_fields=['numero_pasaporte', 'cedula_identidad'])
        
    print(f"Migración completada con éxito.")
    print(f"- Pasaportes migrados: {count_pass}")
    print(f"- Cédulas migradas: {count_ci}")
    print(f"- Otros documentos (asignados a cédula): {count_otro}")

if __name__ == '__main__':
    migrate_docs()

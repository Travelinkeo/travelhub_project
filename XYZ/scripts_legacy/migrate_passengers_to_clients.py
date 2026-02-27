
import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.boletos import BoletoImportado
from core.models.personas import Cliente
from django.db import transaction

def clean_foid(foid):
    if not foid:
        return None
    # Remove common prefixes like DOCS/P/VE/, NI/, etc.
    # Pattern: remove non-alphanumeric characters except hyphens?
    # Or strict extraction of the number part?
    # Example: DOCS/P/VE/15612345/ -> 15612345
    
    # Strategy: split by '/' and take the longest numeric-ish segment, or the one that looks like a doc number
    parts = foid.split('/')
    for part in parts:
        part = part.strip()
        # If part is mostly digits and length > 4, it's likely the ID
        if re.search(r'\d{5,}', part):
            return part
            
    # Fallback: if no clear ID found, return the original string stripped
    return foid.strip()

def split_name(full_name):
    if not full_name:
        return "Unknown", "Unknown"
    
    # Format usually LASTNAME/FIRSTNAME
    if '/' in full_name:
        parts = full_name.split('/')
        apellidos = parts[0].strip()
        nombres = parts[1].strip() if len(parts) > 1 else ""
    else:
        # Try splitting by space
        parts = full_name.strip().split()
        if len(parts) >= 2:
            apellidos = parts[0]
            nombres = " ".join(parts[1:])
        else:
            apellidos = full_name
            nombres = ""
            
    return nombres, apellidos

def migrate():
    boletos = BoletoImportado.objects.exclude(nombre_pasajero_procesado__isnull=True).exclude(foid_pasajero__isnull=True)
    
    created_count = 0
    skipped_count = 0
    
    print(f"Found {boletos.count()} boletos with passenger data.")
    
    with transaction.atomic():
        for b in boletos:
            nombre_raw = b.nombre_pasajero_procesado
            foid_raw = b.foid_pasajero
            
            if not nombre_raw or not foid_raw:
                continue
                
            doc_number = clean_foid(foid_raw)
            nombres, apellidos = split_name(nombre_raw)
            
            # Check if client exists by document (using numero_pasaporte as the main ID for now)
            if Cliente.objects.filter(numero_pasaporte=doc_number).exists():
                skipped_count += 1
                continue
            
            # Create Client
            try:
                Cliente.objects.create(
                    nombres=nombres,
                    apellidos=apellidos,
                    numero_pasaporte=doc_number,
                    # Cliente model doesn't have tipo_documento, assuming passport/doc is stored in numero_pasaporte
                    notas_cliente=f"Importado automáticamente desde Boleto {b.numero_boleto}",
                    tipo_cliente=Cliente.TipoCliente.INDIVIDUAL
                )
                created_count += 1
                print(f"Created: {nombres} {apellidos} ({doc_number})")
            except Exception as e:
                print(f"Error creating {nombres} {apellidos}: {e}")

    print(f"Migration finished. Created: {created_count}, Skipped: {skipped_count}")

if __name__ == '__main__':
    migrate()

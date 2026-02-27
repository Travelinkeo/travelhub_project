
import os
import django
import sys
from django.utils import timezone
from datetime import timedelta

# Setup Django
sys.path.append('c:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado
from django.db.models import Count

def audit_incidents():
    print("--- AUDITORÍA DE INCIDENCIAS EN BASE DE DATOS ---")
    
    total = BoletoImportado.objects.count()
    print(f"Total de boletos en BD: {total}")
    
    # 1. Resumen por estado
    estados = BoletoImportado.objects.values('estado_parseo').annotate(total=Count('id_boleto_importado')).order_by('-total')
    print("\nResumen por Estado de Parseo:")
    for e in estados:
        print(f"  - {e['estado_parseo']}: {e['total']}")
        
    # 2. Resumen por formato detectado
    formatos = BoletoImportado.objects.values('formato_detectado').annotate(total=Count('id_boleto_importado')).order_by('-total')
    print("\nResumen por Formato Detectado:")
    for f in formatos:
        print(f"  - {f['formato_detectado']}: {f['total']}")

    # 3. Incidencias Recientes (últimas 24h con Error)
    hace_24h = timezone.now() - timedelta(hours=24)
    recientes_error = BoletoImportado.objects.filter(estado_parseo='ERR', fecha_subida__gte=hace_24h)
    print(f"\nIncidencias con ERROR en las últimas 24h: {recientes_error.count()}")
    for b in recientes_error[:10]:
        print(f"  ID: {b.id_boleto_importado} | Archivo: {os.path.basename(b.archivo_boleto.name)} | Log: {str(b.log_parseo)[:100]}...")

    # 4. Boletos Pendientes Antiguos (> 1 hora)
    hace_1h = timezone.now() - timedelta(hours=1)
    pendientes_antiguos = BoletoImportado.objects.filter(estado_parseo='PEN', fecha_subida__lt=hace_1h)
    print(f"\nBoletos PENDIENTES estancados (>1 hora): {pendientes_antiguos.count()}")
    for b in pendientes_antiguos[:10]:
        print(f"  ID: {b.id_boleto_importado} | Archivo: {os.path.basename(b.archivo_boleto.name)} | Creado: {b.fecha_subida}")

    # 5. Análisis de logs de error recurrentes
    print("\nLogs de Error Recurrentes (Top 5):")
    errors = BoletoImportado.objects.filter(estado_parseo='ERR').values('log_parseo').annotate(total=Count('id_boleto_importado')).order_by('-total')[:5]
    for err in errors:
        snippet = str(err['log_parseo'])[:80].replace('\n', ' ')
        print(f"  - ({err['total']} veces): {snippet}...")

if __name__ == "__main__":
    audit_incidents()

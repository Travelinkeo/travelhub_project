
import os
import sys
import django
from decimal import Decimal
from django.core.files.base import ContentFile

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.models import ReporteProveedor, ItemReporte
from apps.finance.services.reconciliation_service import ReconciliationService
from apps.bookings.models import BoletoImportado
from core.models_catalogos import Proveedor

def verify_reconciliation():
    print("--- Verificando Módulo de Conciliación ---")

    # 1. Crear Datos de Prueba (Proveedor)
    proveedor, _ = Proveedor.objects.get_or_create(
        nombre="Aerolinea Test", 
        defaults={'rif': 'J-12345678-9', 'tipo_proveedor': 'AIR'}
    )

    # 2. Crear Boleto en Sistema (para que haya match)
    boleto_num = "9991234567890"
    boleto_sys, _ = BoletoImportado.objects.get_or_create(
        numero_boleto=boleto_num,
        defaults={
            'nombre_pasajero_completo': 'JUAN PEREZ',
            'total_boleto': Decimal('510.00'),
            'comision_agencia': Decimal('50.00')
        }
    )
    print(f"✅ Boleto en Sistema: {boleto_num} (Monto: {boleto_sys.total_boleto})")

    # 3. Crear CSV Dummy
    csv_content = f"""Boleto,Pasajero,Monto_Neto,Impuestos,Comision
{boleto_num},JUAN PEREZ,500.00,10.00,50.00
9990000000000,MARIA GOMEZ,300.00,5.00,30.00
"""
    
    # 4. Crear Reporte
    reporte = ReporteProveedor.objects.create(
        proveedor=proveedor,
        estado=ReporteProveedor.EstadoReporte.PENDIENTE
    )
    reporte.archivo.save('test_bsp.csv', ContentFile(csv_content))
    print(f"✅ Reporte creado: {reporte}")

    # 5. Procesar
    print("🔄 Procesando reporte...")
    ReconciliationService.process_report(reporte.id)

    # 6. Verificar Resultados
    items = reporte.items.all()
    print(f"📊 Items procesados: {items.count()}")

    for item in items:
        status_icon = "❓"
        if item.estado == ItemReporte.EstadoConciliacion.MATCH:
            status_icon = "✅ MATCH"
        elif item.estado == ItemReporte.EstadoConciliacion.MISSING_INTERNAL:
            status_icon = "❌ NO FOUND"
        
        print(f"   - Ticket: {item.numero_boleto} -> {status_icon} (Monto Proveedor: {item.monto_total_proveedor})")

    # Validaciones
    item_match = items.get(numero_boleto=boleto_num)
    assert item_match.estado == ItemReporte.EstadoConciliacion.MATCH, "El boleto existente debió conciliarse"
    
    item_no_exist = items.get(numero_boleto="9990000000000")
    assert item_no_exist.estado == ItemReporte.EstadoConciliacion.MISSING_INTERNAL, "El boleto inexistente debió marcarse como MISSING_INTERNAL"

    print("\n🎉 VERIFICACIÓN EXITOSA: La lógica de conciliación funciona.")

if __name__ == "__main__":
    try:
        verify_reconciliation()
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

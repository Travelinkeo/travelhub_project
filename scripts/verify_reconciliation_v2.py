
import os
import sys
import django
from decimal import Decimal
from django.core.files.base import ContentFile

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.models import ReporteProveedor, ItemReporte, DiferenciaFinanciera
from apps.finance.services.reconciliation_service import ReconciliationService
from apps.bookings.models import BoletoImportado
from core.models import Proveedor, Agencia

def verify_reconciliation_v2():
    print("--- Iniciando Verificacion de Conciliacion AI v2 ---")

    # 1. Setup Agencia y Proveedor
    from django.contrib.auth.models import User
    propietario, _ = User.objects.get_or_create(username="test_owner")
    agencia, _ = Agencia.objects.get_or_create(
        nombre="Agencia AI Test", 
        defaults={'activa': True, 'propietario': propietario}
    )
    proveedor, _ = Proveedor.objects.get_or_create(
        nombre="BSP IA GLOBAL", 
        defaults={'rif': 'J-99999999-9', 'tipo_proveedor': 'AIR', 'agencia': agencia}
    )

    # 2. Crear Boletos Internos
    # Boleto 1: Match Perfecto
    tkt_ok = "1230000000001"
    BoletoImportado.objects.get_or_create(
        numero_boleto=tkt_ok,
        agencia=agencia,
        defaults={'total_boleto': Decimal('150.00'), 'nombre_pasajero_completo': 'ALEMAN/JOSE'}
    )

    # Boleto 2: Discrepancia Financiera
    tkt_diff = "1230000000002"
    BoletoImportado.objects.get_or_create(
        numero_boleto=tkt_diff,
        agencia=agencia,
        defaults={'total_boleto': Decimal('200.00'), 'nombre_pasajero_completo': 'PEREZ/JUAN'}
    )

    print(f"(OK) Datos internos preparados para agencia: {agencia.nombre}")

    # 3. Crear CSV "Sucio" (para probar Smart Mapping)
    csv_content = """Ticket#,Guest Name,FinalPrice,Fee,IATADate
1230000000001,ALEMAN JOSE,150.00,0,2026-02-22
1230000000002,PEREZ JUAN,205.50,5.50,2026-02-22
9990000000000,GHOST PASSENGER,100.00,0,2026-02-22
"""
    
    # 4. Crear y Procesar Reporte
    reporte = ReporteProveedor.objects.create(
        proveedor=proveedor,
        agencia=agencia,
        estado=ReporteProveedor.EstadoReporte.PENDIENTE
    )
    reporte.archivo.save('bsp_messy_report.csv', ContentFile(csv_content))
    print(f"(PROCESS) Reporte cargado. Ejecutando motor de IA...")

    try:
        ReconciliationService.process_report(reporte.id)
        
        # 5. Verificar Resultados
        reporte.refresh_from_db()
        print(f"\nRESUMEN FINAL ({reporte.get_estado_display()}):")
        print(f"   - Total Registros: {reporte.total_registros}")
        print(f"   - Con Diferencias: {reporte.total_con_diferencia}")

        for item in reporte.items.all().order_by('numero_boleto'):
            status = "MATCH OK" if item.estado == 'MAT' else "DISCREPANCIA" if item.estado == 'DIS' else "NO ENCONTRADO"
            print(f"   [{status}] Tkt: {item.numero_boleto} | Pasajero: {item.pasajero} | Sistema: ${item.monto_sistema} | Proveedor: ${item.monto_total_proveedor}")
            
            for d in item.diferencias.all():
                print(f"      -> DISCREPANCIA EN {d.campo_discrepancia}: +${d.diferencia}")

        # Validaciones
        if reporte.total_registros == 3:
            print("\nSUCCES: La prueba ha detectado los 3 registros correctamente.")
        else:
            print("\nERROR: Numero de registros incorrecto.")

        print("\nPrueba finalizada exitosamente.")

    except Exception as e:
        print(f"\nERROR EN VERIFICACION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_reconciliation_v2()

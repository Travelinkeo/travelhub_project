import os
import django
import sys
from decimal import Decimal

# Setup Django
sys.path.append(r'C:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.models.reconciliacion import ConciliacionBoleto, ReporteReconciliacion
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService
from apps.contabilidad.models import AsientoContable, DetalleAsiento

def test_ajuste():
    # Mock a reconciliation with discrepancy
    conciliacion = ConciliacionBoleto.objects.filter(estado='DISCREPANCIA').first()
    if not conciliacion:
        print("No hay conciliaciones con discrepancia para probar.")
        return

    print(f"Probando para Conciliacion ID: {conciliacion.id_conciliacion}, Dif: {conciliacion.diferencia_total}")
    
    SmartReconciliationService.proponer_asiento_ajuste(conciliacion)
    
    # Reload and check
    conciliacion.refresh_from_db()
    asiento = conciliacion.sugerencia_asiento
    
    if asiento:
        print(f"Asiento generado: {asiento.id_asiento}")
        print(f"Descripción: {asiento.descripcion_general}")
        detalles = asiento.detalles_asiento.all()
        print(f"Detalles encontrados: {detalles.count()}")
        for det in detalles:
            print(f" - {det.cuenta_contable.codigo_cuenta}: D {det.debe} | H {det.haber}")
        
        if asiento.esta_cuadrado:
            print("PASA: Asiento cuadrado")
        else:
            print("FALLA: Asiento descuadrado")
    else:
        print("FALLA: No se generó asiento.")

if __name__ == "__main__":
    test_ajuste()

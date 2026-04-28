import os
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.contabilidad.models import PlanContable

def initialize_accounts():
    accounts = [
        # ACTIVOS
        {'codigo': '1.1.02.02', 'nombre': 'Cuentas por Cobrar USD', 'tipo': 'AC', 'naturaleza': 'D', 'nivel': 4},
        
        # PASIVOS
        {'codigo': '2.1.01.02', 'nombre': 'Cuentas por Pagar Proveedores USD', 'tipo': 'PA', 'naturaleza': 'H', 'nivel': 4},
        {'codigo': '2.1.02.01', 'nombre': 'IVA Débito Fiscal', 'tipo': 'PA', 'naturaleza': 'H', 'nivel': 4},
        {'codigo': '2.1.02.03', 'nombre': 'IGTF por Pagar (3%)', 'tipo': 'PA', 'naturaleza': 'H', 'nivel': 4},
        
        # INGRESOS
        {'codigo': '4.1.01', 'nombre': 'Comisiones Boletos Aéreos', 'tipo': 'IN', 'naturaleza': 'H', 'nivel': 3},
        {'codigo': '4.2', 'nombre': 'Ingresos por Venta de Paquetes', 'tipo': 'IN', 'naturaleza': 'H', 'nivel': 2},
    ]

    for acc in accounts:
        obj, created = PlanContable.objects.get_or_create(
            codigo_cuenta=acc['codigo'],
            defaults={
                'nombre_cuenta': acc['nombre'],
                'tipo_cuenta': acc['tipo'],
                'naturaleza': acc['naturaleza'],
                'nivel': acc['nivel'],
                'permite_movimientos': True
            }
        )
        if created:
            print(f"Cuenta creada: {acc['codigo']} - {acc['nombre']}")
        else:
            print(f"Cuenta ya existe: {acc['codigo']}")

if __name__ == "__main__":
    initialize_accounts()

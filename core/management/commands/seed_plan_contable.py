from django.core.management.base import BaseCommand
from core.models.contabilidad import PlanContable
from django.db import transaction

class Command(BaseCommand):
    help = 'Poblar Plan Contable Básico para Agencia de Viajes (Venezuela)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando carga de Plan Contable...")
        
        cuentas = [
            # NIVEL 1: ACTIVOS
            {'codigo': '1', 'nombre': 'ACTIVO', 'tipo': 'AC', 'nivel': 1, 'padre': None, 'movimiento': False, 'nat': 'D'},
            {'codigo': '1.1', 'nombre': 'DISPONIBLE', 'tipo': 'AC', 'nivel': 2, 'padre': '1', 'movimiento': False, 'nat': 'D'},
            {'codigo': '1.1.01', 'nombre': 'Caja Chica (Efectivo)', 'tipo': 'AC', 'nivel': 3, 'padre': '1.1', 'movimiento': True, 'nat': 'D'},
            {'codigo': '1.1.02', 'nombre': 'Banco Nacional (Bs)', 'tipo': 'AC', 'nivel': 3, 'padre': '1.1', 'movimiento': True, 'nat': 'D'},
            {'codigo': '1.1.03', 'nombre': 'Banco Internacional / Zelle', 'tipo': 'AC', 'nivel': 3, 'padre': '1.1', 'movimiento': True, 'nat': 'D'},
            
            # NIVEL 2: PASIVOS
            {'codigo': '2', 'nombre': 'PASIVO', 'tipo': 'PA', 'nivel': 1, 'padre': None, 'movimiento': False, 'nat': 'H'},
            {'codigo': '2.1', 'nombre': 'CUENTAS POR PAGAR', 'tipo': 'PA', 'nivel': 2, 'padre': '2', 'movimiento': False, 'nat': 'H'},
            {'codigo': '2.1.01', 'nombre': 'Proveedores Nacionales', 'tipo': 'PA', 'nivel': 3, 'padre': '2.1', 'movimiento': True, 'nat': 'H'},
            {'codigo': '2.1.02', 'nombre': 'Proveedores Internacionales', 'tipo': 'PA', 'nivel': 3, 'padre': '2.1', 'movimiento': True, 'nat': 'H'},

            # NIVEL 4: INGRESOS
            {'codigo': '4', 'nombre': 'INGRESOS', 'tipo': 'IN', 'nivel': 1, 'padre': None, 'movimiento': False, 'nat': 'H'},
            {'codigo': '4.1', 'nombre': 'VENTAS', 'tipo': 'IN', 'nivel': 2, 'padre': '4', 'movimiento': False, 'nat': 'H'},
            {'codigo': '4.1.01', 'nombre': 'Venta Boletería', 'tipo': 'IN', 'nivel': 3, 'padre': '4.1', 'movimiento': True, 'nat': 'H'},
            {'codigo': '4.1.02', 'nombre': 'Comisiones / Fees', 'tipo': 'IN', 'nivel': 3, 'padre': '4.1', 'movimiento': True, 'nat': 'H'},

            # NIVEL 5: GASTOS (GA) - CRÍTICO PARA EL MÓDULO DE GASTOS
            {'codigo': '5', 'nombre': 'GASTOS', 'tipo': 'GA', 'nivel': 1, 'padre': None, 'movimiento': False, 'nat': 'D'},
            
            {'codigo': '5.1', 'nombre': 'GASTOS DE PERSONAL', 'tipo': 'GA', 'nivel': 2, 'padre': '5', 'movimiento': False, 'nat': 'D'},
            {'codigo': '5.1.01', 'nombre': 'Sueldos y Salarios', 'tipo': 'GA', 'nivel': 3, 'padre': '5.1', 'movimiento': True, 'nat': 'D'},
            {'codigo': '5.1.02', 'nombre': 'Comisiones Vendedores', 'tipo': 'GA', 'nivel': 3, 'padre': '5.1', 'movimiento': True, 'nat': 'D'},
            
            {'codigo': '5.2', 'nombre': 'GASTOS OPERATIVOS', 'tipo': 'GA', 'nivel': 2, 'padre': '5', 'movimiento': False, 'nat': 'D'},
            {'codigo': '5.2.01', 'nombre': 'Alquiler de Oficina', 'tipo': 'GA', 'nivel': 3, 'padre': '5.2', 'movimiento': True, 'nat': 'D'},
            {'codigo': '5.2.02', 'nombre': 'Servicios (Luz, Agua, Internet)', 'tipo': 'GA', 'nivel': 3, 'padre': '5.2', 'movimiento': True, 'nat': 'D'},
            {'codigo': '5.2.03', 'nombre': 'Licencias de Software (GDS, TravelHub)', 'tipo': 'GA', 'nivel': 3, 'padre': '5.2', 'movimiento': True, 'nat': 'D'},
            
            {'codigo': '5.3', 'nombre': 'GASTOS ADMINISTRATIVOS', 'tipo': 'GA', 'nivel': 2, 'padre': '5', 'movimiento': False, 'nat': 'D'},
            {'codigo': '5.3.01', 'nombre': 'Papelería y Útiles', 'tipo': 'GA', 'nivel': 3, 'padre': '5.3', 'movimiento': True, 'nat': 'D'},
            {'codigo': '5.3.02', 'nombre': 'Refrigerios / Café', 'tipo': 'GA', 'nivel': 3, 'padre': '5.3', 'movimiento': True, 'nat': 'D'},
            {'codigo': '5.3.03', 'nombre': 'Transporte / Taxis', 'tipo': 'GA', 'nivel': 3, 'padre': '5.3', 'movimiento': True, 'nat': 'D'},
            
            {'codigo': '5.4', 'nombre': 'GASTOS FINANCIEROS', 'tipo': 'GA', 'nivel': 2, 'padre': '5', 'movimiento': False, 'nat': 'D'},
            {'codigo': '5.4.01', 'nombre': 'Comisiones Bancarias', 'tipo': 'GA', 'nivel': 3, 'padre': '5.4', 'movimiento': True, 'nat': 'D'},
            {'codigo': '5.4.02', 'nombre': 'Impuesto IGTF', 'tipo': 'GA', 'nivel': 3, 'padre': '5.4', 'movimiento': True, 'nat': 'D'},
        ]

        with transaction.atomic():
            creados = 0
            omitidos = 0
            for c in cuentas:
                # Buscar padre
                padre = None
                if c['padre']:
                    padre = PlanContable.objects.filter(codigo_cuenta=c['padre']).first()
                
                obj, created = PlanContable.objects.get_or_create(
                    codigo_cuenta=c['codigo'],
                    defaults={
                        'nombre_cuenta': c['nombre'],
                        'tipo_cuenta': c['tipo'],
                        'nivel': c['nivel'],
                        'cuenta_padre': padre,
                        'permite_movimientos': c['movimiento'],
                        'naturaleza': c['nat']
                    }
                )
                if created:
                    creados += 1
                else:
                    omitidos += 1
            
            self.stdout.write(self.style.SUCCESS(f"Finalizado: {creados} cuentas creadas, {omitidos} existentes."))

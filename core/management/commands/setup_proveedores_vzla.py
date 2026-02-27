from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models_catalogos import Proveedor, Moneda
from core.models.tarifario_hoteles import TarifarioProveedor
from decimal import Decimal

class Command(BaseCommand):
    help = 'Carga proveedores (Consolidadoras) y sus comisiones base para Venezuela'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando carga de Consolidadoras...")

        # 1. Asegurar Moneda
        Moneda.objects.get_or_create(codigo_iso="USD", defaults={'nombre': 'Dólar Americano'})

        # 2. Datos: (Nombre, RIF, % Comisión que nos dan)
        data = [
            ("BT Travel", "J-00000001-0", 5.00),
            ("Maso Turismo", "J-00000002-0", 4.00),
            ("Capi Tours", "J-00000003-0", 6.00),
            ("Viajes Humboldt", "J-00000004-0", 5.00),
            ("Consolidadora Genérica", "J-99999999-9", 0.00)
        ]

        for nombre, rif, comision in data:
            # Ajustar 'rif' o 'numero_identificacion' según el modelo real Proveedor
            prov, created = Proveedor.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'rif': rif,
                    'contacto_email': 'emisiones@ejemplo.com', 
                    'activo': True,
                    'tipo_proveedor': Proveedor.TipoProveedorChoices.CONSOLIDADOR,
                    'nivel_proveedor': Proveedor.NivelProveedorChoices.CONSOLIDADOR
                }
            )
            
            if created:
                 self.stdout.write(f"✅ Proveedor creado: {nombre}")
            else:
                 self.stdout.write(f"ℹ️ Proveedor ya existía: {nombre}")
            
            # Crear Tarifario Activo
            # TarifarioProveedor doesn't have a unique constraint on provider + active easily checked here
            # so we check if there is an active one first
            existing_tarifario = TarifarioProveedor.objects.filter(
                proveedor=prov, 
                activo=True
            ).exists()
            
            if not existing_tarifario:
                TarifarioProveedor.objects.create(
                    proveedor=prov,
                    nombre=f"Comisión Estándar {nombre}",
                    fecha_vigencia_inicio=timezone.now().date(),
                    fecha_vigencia_fin=timezone.now().date().replace(year=2030),
                    comision_estandar=Decimal(str(comision)),
                    activo=True
                )
                self.stdout.write(f"   💰 Tarifario configurado: {comision}%")
            else:
                self.stdout.write(f"   ℹ️ Tarifario activo ya existe")

        self.stdout.write(self.style.SUCCESS('¡Configuración de Agencia Satélite completada!'))

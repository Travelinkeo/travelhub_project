
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Agencia, Moneda, ProductoServicio
from core.models_catalogos import Proveedor
from django.utils import timezone

class Command(BaseCommand):
    help = 'Semilla de datos iniciales para TravelHub (Admin, Agencia, Config)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🌱 Iniciando siembra de datos...'))

        # 1. Superusuario
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@travelhub.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('👤 Superusuario "admin" creado (Pass: admin123)'))
        else:
            self.stdout.write('👤 Superusuario ya existe')

        # 2. Agencia Principal
        admin_user = User.objects.get(username='admin')
        agencia, created = Agencia.objects.get_or_create(
            nombre="Travelinkeo",
            defaults={
                'direccion': 'Caracas, Venezuela',
                'telefono_principal': '+58 412 0000000',
                'email_principal': 'contacto@travelinkeo.com',
                'moneda_principal': 'USD',
                'propietario': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'🏢 Agencia "{agencia.nombre}" creada'))

        # 3. Monedas
        moneda_usd, _ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre': 'Dólar Americano', 'simbolo': '$', 'es_moneda_local': False})
        moneda_ves, _ = Moneda.objects.get_or_create(codigo_iso='VES', defaults={'nombre': 'Bolívar Soberano', 'simbolo': 'Bs.', 'es_moneda_local': True})
        moneda_eur, _ = Moneda.objects.get_or_create(codigo_iso='EUR', defaults={'nombre': 'Euro', 'simbolo': '€', 'es_moneda_local': False})
        
        self.stdout.write(self.style.SUCCESS('💰 Monedas creadas'))

        # 3.1 Tipos de Cambio (Ejemplo: Hoy)
        from core.models_catalogos import TipoCambio
        # USD -> VES
        TipoCambio.objects.get_or_create(
            moneda_origen=moneda_usd,
            moneda_destino=moneda_ves,
            fecha_efectiva=timezone.now().date(),
            defaults={'tasa_conversion': 70.00}
        )
        # EUR -> USD
        TipoCambio.objects.get_or_create(
            moneda_origen=moneda_eur,
            moneda_destino=moneda_usd,
            fecha_efectiva=timezone.now().date(),
            defaults={'tasa_conversion': 1.05}
        )

        # 4. Productos Base (Para que el sistema no falle al crear items)
        ProductoServicio.objects.get_or_create(
            codigo_interno="TKT-AIR",
            defaults={'nombre': 'Boleto Aéreo', 'tipo_producto': 'AIR', 'descripcion': 'Emisión de boleto aéreo'}
        )
        ProductoServicio.objects.get_or_create(
            codigo_interno="FEE-SERV",
            defaults={'nombre': 'Fee de Servicio', 'tipo_producto': 'FEE', 'descripcion': 'Honorarios por gestión'}
        )
        self.stdout.write(self.style.SUCCESS('📦 Productos base creados'))
        
        # 5. Proveedores Genericos (Ejemplo)
        # Asegurar que importamos Proveedor
        from core.models_catalogos import Proveedor
        Proveedor.objects.get_or_create(
            nombre="IATA GENERICO",
            defaults={'tipo_proveedor': 'AER', 'identificadores_gds': {'IATA': ['999']}}
        )

        self.stdout.write(self.style.SUCCESS('✅ ¡Semillas plantadas correctamente!'))

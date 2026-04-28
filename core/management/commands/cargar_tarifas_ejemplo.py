from django.core.management.base import BaseCommand
from core.models import HotelTarifario, TipoHabitacion, TarifaHabitacion
from decimal import Decimal
from datetime import date

class Command(BaseCommand):
    help = 'Carga tarifas de ejemplo para todos los hoteles'
    
    def handle(self, *args, **options):
        hoteles = HotelTarifario.objects.filter(activo=True)
        
        for hotel in hoteles:
            # Crear tipo de habitación si no existe
            tipo_hab, created = TipoHabitacion.objects.get_or_create(
                hotel=hotel,
                nombre='STANDARD',
                defaults={
                    'capacidad_adultos': 2,
                    'capacidad_ninos': 2,
                    'capacidad_total': 4
                }
            )
            
            # Eliminar tarifas existentes
            tipo_hab.tarifas.all().delete()
            
            # Crear tarifas de ejemplo (temporada baja)
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2025, 9, 21),
                fecha_fin=date(2025, 12, 19),
                nombre_temporada='Temporada Baja',
                tarifa_sgl=Decimal('60.00'),
                tarifa_dbl=Decimal('70.00'),
                tarifa_tpl=Decimal('85.00'),
                tarifa_pax_adicional=Decimal('25.00'),
                tarifa_nino_4_10=Decimal('15.00')
            )
            
            # Navidad
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2025, 12, 20),
                fecha_fin=date(2025, 12, 27),
                nombre_temporada='NAVIDAD',
                tarifa_sgl=Decimal('90.00'),
                tarifa_dbl=Decimal('110.00'),
                tarifa_tpl=Decimal('135.00'),
                tarifa_pax_adicional=Decimal('35.00'),
                tarifa_nino_4_10=Decimal('25.00')
            )
            
            # Fin de año
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2025, 12, 28),
                fecha_fin=date(2026, 1, 5),
                nombre_temporada='FIN DE AÑO',
                tarifa_sgl=Decimal('120.00'),
                tarifa_dbl=Decimal('150.00'),
                tarifa_tpl=Decimal('180.00'),
                tarifa_pax_adicional=Decimal('45.00'),
                tarifa_nino_4_10=Decimal('30.00')
            )
            
            # Temporada regular
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2026, 1, 6),
                fecha_fin=date(2026, 1, 15),
                nombre_temporada='Regular',
                tarifa_sgl=Decimal('65.00'),
                tarifa_dbl=Decimal('75.00'),
                tarifa_tpl=Decimal('90.00'),
                tarifa_pax_adicional=Decimal('28.00'),
                tarifa_nino_4_10=Decimal('18.00')
            )
            
            self.stdout.write(f'Tarifas creadas para: {hotel.nombre}')
        
        self.stdout.write(self.style.SUCCESS(f'Tarifas cargadas para {hoteles.count()} hoteles'))

from django.core.management.base import BaseCommand
from core.models import HotelTarifario, TipoHabitacion, TarifaHabitacion
from decimal import Decimal
from datetime import date
import random

class Command(BaseCommand):
    help = 'Completa tarifas para hoteles sin tarifas'
    
    def handle(self, *args, **options):
        hoteles = HotelTarifario.objects.filter(activo=True)
        
        # Precios base por destino y régimen
        precios_base = {
            ('Isla Margarita', 'TI'): 80,
            ('Isla Margarita', 'SD'): 50,
            ('Los Roques', 'TI'): 150,
            ('Los Roques', 'SD'): 100,
            ('Mérida', 'SD'): 40,
            ('Caracas', 'SD'): 60,
        }
        
        for hotel in hoteles:
            # Verificar si ya tiene tarifas
            if hotel.tipos_habitacion.filter(tarifas__isnull=False).exists():
                continue
            
            # Crear tipo de habitación
            tipo_hab, _ = TipoHabitacion.objects.get_or_create(
                hotel=hotel,
                nombre='ESTÁNDAR',
                defaults={'capacidad_adultos': 2, 'capacidad_ninos': 2, 'capacidad_total': 4}
            )
            
            # Precio base según destino y régimen
            key = (hotel.destino, hotel.regimen)
            base = precios_base.get(key, 60)
            
            # Variación aleatoria ±20%
            variacion = random.uniform(0.8, 1.2)
            base = int(base * variacion)
            
            # Temporada baja
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2025, 9, 16),
                fecha_fin=date(2025, 12, 18),
                nombre_temporada='TEMPORADA BAJA',
                tarifa_sgl=Decimal(str(base * 1.5)),
                tarifa_dbl=Decimal(str(base)),
                tarifa_tpl=Decimal(str(base)),
                tarifa_nino_4_10=Decimal(str(base * 0.6))
            )
            
            # Navidad
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2025, 12, 19),
                fecha_fin=date(2025, 12, 27),
                nombre_temporada='NAVIDAD',
                tarifa_sgl=Decimal(str(base * 1.9)),
                tarifa_dbl=Decimal(str(base * 1.25)),
                tarifa_tpl=Decimal(str(base * 1.25)),
                tarifa_nino_4_10=Decimal(str(base * 0.75))
            )
            
            # Fin de año
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2025, 12, 28),
                fecha_fin=date(2026, 1, 6),
                nombre_temporada='FIN DE AÑO',
                tarifa_sgl=Decimal(str(base * 2.75)),
                tarifa_dbl=Decimal(str(base * 1.83)),
                tarifa_tpl=Decimal(str(base * 1.83)),
                tarifa_nino_4_10=Decimal(str(base * 1.1))
            )
            
            # Temporada regular
            TarifaHabitacion.objects.create(
                tipo_habitacion=tipo_hab,
                fecha_inicio=date(2026, 1, 7),
                fecha_fin=date(2026, 2, 17),
                nombre_temporada='TEMPORADA BAJA',
                tarifa_sgl=Decimal(str(base * 1.6)),
                tarifa_dbl=Decimal(str(base * 1.08)),
                tarifa_tpl=Decimal(str(base * 1.08)),
                tarifa_nino_4_10=Decimal(str(base * 0.65))
            )
            
            self.stdout.write(f'Tarifas creadas para: {hotel.nombre} (base: ${base})')
        
        total = HotelTarifario.objects.filter(tipos_habitacion__tarifas__isnull=False).distinct().count()
        self.stdout.write(self.style.SUCCESS(f'Total hoteles con tarifas: {total}'))

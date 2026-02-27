import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import HotelTarifario, TipoHabitacion, TarifaHabitacion
from decimal import Decimal
from datetime import date

# Datos extraídos manualmente del JSON/PDF
hoteles_morrocoy = [
    {
        'nombre': 'PARADISE ADÍCORA',
        'tipos_habitacion': [
            {
                'nombre': 'ESTÁNDAR JARDÍN',
                'tarifas': [
                    {'inicio': '2025-06-01', 'fin': '2025-12-25', 'temporada': 'Lunes a Jueves', 'moneda': 'EUR', 'sgl': 60, 'dbl': 60, 'tpl': 72},
                    {'inicio': '2025-06-01', 'fin': '2025-12-26', 'temporada': 'Viernes a Domingo', 'moneda': 'EUR', 'sgl': 84, 'dbl': 96, 'tpl': 108},
                ]
            },
            {
                'nombre': 'SUPERIOR VISTA AL MAR',
                'tarifas': [
                    {'inicio': '2025-06-01', 'fin': '2025-12-25', 'temporada': 'Lunes a Jueves', 'moneda': 'EUR', 'sgl': 96, 'dbl': 96, 'tpl': 108},
                ]
            }
        ]
    },
    {
        'nombre': 'PARAISO AZUL',
        'tipos_habitacion': [
            {
                'nombre': 'TODO INCLUIDO',
                'tarifas': [
                    {'inicio': '2025-09-16', 'fin': '2025-10-31', 'temporada': 'Lunes a Jueves', 'moneda': 'USD', 'sgl': 221, 'dbl': 170, 'tpl': 170, 'chd': 85},
                    {'inicio': '2025-09-16', 'fin': '2025-10-31', 'temporada': 'Viernes a Domingo', 'moneda': 'USD', 'sgl': 260, 'dbl': 200, 'tpl': 200, 'chd': 100},
                ]
            }
        ]
    },
    {
        'nombre': 'POSADA LA ARDILEÑA',
        'tipos_habitacion': [
            {
                'nombre': 'STANDARD',
                'tarifas': [
                    {'inicio': '2025-08-01', 'fin': '2025-11-30', 'temporada': 'Fin de Semana', 'moneda': 'EUR', 'sgl': 464.44, 'dbl': 232.22, 'tpl': 232.22, 'chd': 116.11},
                    {'inicio': '2025-08-01', 'fin': '2025-11-30', 'temporada': 'Entre Semana', 'moneda': 'EUR', 'sgl': 420, 'dbl': 210, 'tpl': 210, 'chd': 105},
                ]
            }
        ]
    },
    {
        'nombre': 'HOTEL ISLA LINDA',
        'tipos_habitacion': [
            {
                'nombre': 'QUEEN VISTA JARDÍN',
                'tarifas': [
                    {'inicio': '2025-09-12', 'fin': '2025-11-30', 'temporada': 'Regular', 'moneda': 'EUR', 'sgl': 170, 'dbl': 170, 'chd': 20},
                ]
            },
            {
                'nombre': 'QUEEN DOBLE VISTA JARDÍN',
                'tarifas': [
                    {'inicio': '2025-09-12', 'fin': '2025-11-30', 'temporada': 'Regular', 'moneda': 'EUR', 'dbl': 240, 'tpl': 240, 'chd': 20},
                ]
            }
        ]
    },
    {
        'nombre': 'HESPERIA MORROCOY',
        'tipos_habitacion': [
            {
                'nombre': 'ESTÁNDAR BASIC',
                'tarifas': [
                    {'inicio': '2025-09-16', 'fin': '2025-12-21', 'temporada': 'Temporada Baja', 'moneda': 'USD', 'sgl': 110, 'dbl': 80, 'chd': 40},
                    {'inicio': '2025-12-22', 'fin': '2025-12-28', 'temporada': 'Navidad', 'moneda': 'USD', 'sgl': 150, 'dbl': 120, 'chd': 60},
                ]
            },
            {
                'nombre': 'ESTÁNDAR DELUXE',
                'tarifas': [
                    {'inicio': '2025-09-16', 'fin': '2025-12-21', 'temporada': 'Temporada Baja', 'moneda': 'USD', 'sgl': 130, 'dbl': 100, 'chd': 50},
                ]
            }
        ]
    }
]

# Cargar en la base de datos
for hotel_data in hoteles_morrocoy:
    try:
        hotel = HotelTarifario.objects.get(nombre=hotel_data['nombre'], destino='Morrocoy')
        print(f"\nProcesando: {hotel.nombre}")
        
        # Eliminar tarifas existentes
        for tipo_hab in hotel.tipos_habitacion.all():
            tipo_hab.tarifas.all().delete()
            tipo_hab.delete()
        
        # Crear tipos de habitación y tarifas
        for tipo_data in hotel_data['tipos_habitacion']:
            tipo_hab = TipoHabitacion.objects.create(
                hotel=hotel,
                nombre=tipo_data['nombre'],
                capacidad_adultos=2,
                capacidad_ninos=2,
                capacidad_total=4
            )
            
            for tarifa_data in tipo_data['tarifas']:
                TarifaHabitacion.objects.create(
                    tipo_habitacion=tipo_hab,
                    fecha_inicio=date.fromisoformat(tarifa_data['inicio']),
                    fecha_fin=date.fromisoformat(tarifa_data['fin']),
                    nombre_temporada=tarifa_data['temporada'],
                    moneda=tarifa_data['moneda'],
                    tarifa_sgl=Decimal(str(tarifa_data.get('sgl', 0))) if tarifa_data.get('sgl') else None,
                    tarifa_dbl=Decimal(str(tarifa_data.get('dbl', 0))) if tarifa_data.get('dbl') else None,
                    tarifa_tpl=Decimal(str(tarifa_data.get('tpl', 0))) if tarifa_data.get('tpl') else None,
                    tarifa_nino_4_10=Decimal(str(tarifa_data.get('chd', 0))) if tarifa_data.get('chd') else None,
                )
            
            print(f"  OK {tipo_hab.nombre}: {tipo_hab.tarifas.count()} tarifas")
        
    except HotelTarifario.DoesNotExist:
        print(f"  ERROR Hotel no encontrado: {hotel_data['nombre']}")

print("\nCarga manual completada")

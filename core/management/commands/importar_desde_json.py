from django.core.management.base import BaseCommand
from core.models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion
from personas.models import Proveedor
from datetime import datetime
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Importa hoteles desde JSON estructurado'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Ruta al archivo JSON')
        parser.add_argument('--proveedor-id', type=int, required=True)

    def handle(self, *args, **options):
        json_path = options['json_path']
        proveedor_id = options['proveedor_id']

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        proveedor = Proveedor.objects.get(id_proveedor=proveedor_id)

        # Crear o obtener tarifario
        tarifario, created = TarifarioProveedor.objects.get_or_create(
            proveedor=proveedor,
            nombre=data.get('nombre_tarifario', 'Tarifario Importado'),
            defaults={
                'fecha_vigencia_inicio': datetime.strptime(data['vigencia']['inicio'], '%Y-%m-%d').date(),
                'fecha_vigencia_fin': datetime.strptime(data['vigencia']['fin'], '%Y-%m-%d').date(),
                'comision_estandar': Decimal(data.get('comision_estandar', '15.00'))
            }
        )

        hoteles_creados = 0
        tarifas_creadas = 0

        for hotel_data in data.get('hoteles', []):
            # Crear hotel
            hotel, created = HotelTarifario.objects.get_or_create(
                tarifario=tarifario,
                nombre=hotel_data['nombre'],
                defaults={
                    'destino': data.get('destino', hotel_data.get('destino', '')),
                    'ubicacion_descripcion': hotel_data.get('ubicacion', ''),
                    'regimen': self._parse_regimen(hotel_data.get('regimen', 'SD')),
                    'comision': Decimal(hotel_data.get('comision', data.get('comision_estandar', '15.00'))),
                    'politica_ninos': hotel_data.get('politica_ninos', ''),
                    'minimo_noches_temporada_baja': hotel_data.get('minimo_noches_baja', 1),
                    'minimo_noches_temporada_alta': hotel_data.get('minimo_noches_alta', 2)
                }
            )

            if created:
                hoteles_creados += 1

            # Crear tipos de habitación y tarifas
            for hab_data in hotel_data.get('habitaciones', []):
                tipo_hab, _ = TipoHabitacion.objects.get_or_create(
                    hotel=hotel,
                    nombre=hab_data['tipo'],
                    defaults={
                        'capacidad_adultos': hab_data.get('capacidad_adultos', 2),
                        'capacidad_ninos': hab_data.get('capacidad_ninos', 0),
                        'capacidad_total': hab_data.get('capacidad_total', 2)
                    }
                )

                # Crear tarifas por temporada
                for tarifa_data in hab_data.get('tarifas', []):
                    TarifaHabitacion.objects.get_or_create(
                        tipo_habitacion=tipo_hab,
                        fecha_inicio=datetime.strptime(tarifa_data['fecha_inicio'], '%Y-%m-%d').date(),
                        fecha_fin=datetime.strptime(tarifa_data['fecha_fin'], '%Y-%m-%d').date(),
                        defaults={
                            'nombre_temporada': tarifa_data.get('temporada', ''),
                            'moneda': tarifa_data.get('moneda', 'USD'),
                            'tarifa_sgl': self._parse_decimal(tarifa_data.get('sgl')),
                            'tarifa_dbl': self._parse_decimal(tarifa_data.get('dbl')),
                            'tarifa_tpl': self._parse_decimal(tarifa_data.get('tpl')),
                            'tarifa_cdp': self._parse_decimal(tarifa_data.get('cdp')),
                            'tarifa_qpl': self._parse_decimal(tarifa_data.get('qpl')),
                            'tarifa_pax_adicional': self._parse_decimal(tarifa_data.get('pax_adicional')),
                            'tarifa_nino_4_10': self._parse_decimal(tarifa_data.get('nino'))
                        }
                    )
                    tarifas_creadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'Importacion completa: {hoteles_creados} hoteles, {tarifas_creadas} tarifas'
        ))

    def _parse_regimen(self, regimen_str):
        regimen_map = {
            'SOLO ALOJAMIENTO': 'SO',
            'SOLO DESAYUNO': 'SD',
            'MEDIA PENSION': 'MP',
            'PENSION COMPLETA': 'PC',
            'TODO INCLUIDO': 'TI',
            'FULL PENSION': 'PC'
        }
        return regimen_map.get(regimen_str.upper(), 'SD')

    def _parse_decimal(self, value):
        if value is None or value == 'N/A':
            return None
        return Decimal(str(value))

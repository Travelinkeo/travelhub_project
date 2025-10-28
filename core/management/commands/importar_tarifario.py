from django.core.management.base import BaseCommand
from django.db import transaction
from core.services.tarifario_parser import TarifarioParser
from core.models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion
from core.models_catalogos import Proveedor
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Importa tarifario de hoteles desde PDF'
    
    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='Ruta al archivo PDF del tarifario')
        parser.add_argument('--proveedor-id', type=int, required=True, help='ID del proveedor')
        parser.add_argument('--nombre', type=str, default='Tarifario Nacional', help='Nombre del tarifario')
        parser.add_argument('--fecha-inicio', type=str, help='Fecha inicio vigencia (YYYY-MM-DD)')
        parser.add_argument('--fecha-fin', type=str, help='Fecha fin vigencia (YYYY-MM-DD)')
    
    def handle(self, *args, **options):
        pdf_path = options['pdf_path']
        proveedor_id = options['proveedor_id']
        nombre = options['nombre']
        
        # Validar proveedor
        try:
            proveedor = Proveedor.objects.get(id_proveedor=proveedor_id)
        except Proveedor.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Proveedor con ID {proveedor_id} no existe'))
            return
        
        # Fechas de vigencia
        if options['fecha_inicio']:
            fecha_inicio = datetime.strptime(options['fecha_inicio'], '%Y-%m-%d').date()
        else:
            fecha_inicio = datetime.now().date()
        
        if options['fecha_fin']:
            fecha_fin = datetime.strptime(options['fecha_fin'], '%Y-%m-%d').date()
        else:
            fecha_fin = fecha_inicio + timedelta(days=365)
        
        self.stdout.write(f'Iniciando importacion de tarifario...')
        self.stdout.write(f'Proveedor: {proveedor.nombre}')
        self.stdout.write(f'Archivo: {pdf_path}')
        
        # Parsear PDF
        try:
            parser = TarifarioParser(pdf_path)
            hoteles_data = parser.extraer_hoteles()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al parsear PDF: {e}'))
            return
        
        if not hoteles_data:
            self.stdout.write(self.style.WARNING('No se encontraron hoteles en el PDF'))
            return
        
        self.stdout.write(f'Hoteles encontrados: {len(hoteles_data)}')
        
        # Crear tarifario
        tarifario = TarifarioProveedor.objects.create(
            proveedor=proveedor,
            nombre=nombre,
            fecha_vigencia_inicio=fecha_inicio,
            fecha_vigencia_fin=fecha_fin,
            comision_estandar=15.00
        )
        
        self.stdout.write(self.style.SUCCESS(f'Tarifario creado: {tarifario.nombre}'))
        
        # Importar hoteles
        hoteles_creados = 0
        tipos_hab_creados = 0
        tarifas_creadas = 0
        hoteles_vistos = set()
        
        for hotel_data in hoteles_data:
            # Evitar duplicados
            hotel_key = f"{hotel_data['nombre']}_{hotel_data['regimen']}"
            if hotel_key in hoteles_vistos:
                continue
            hoteles_vistos.add(hotel_key)
            
            try:
                with transaction.atomic():
                    # Crear hotel
                    hotel = HotelTarifario.objects.create(
                        tarifario=tarifario,
                        nombre=hotel_data['nombre'],
                        destino=hotel_data['destino'],
                        regimen=hotel_data['regimen'],
                        comision=hotel_data['comision'],
                        ubicacion_descripcion=hotel_data.get('ubicacion', ''),
                        politica_ninos=hotel_data['politicas'].get('ninos', ''),
                        check_in=hotel_data['politicas'].get('check_in', '15:00'),
                        check_out=hotel_data['politicas'].get('check_out', '12:00'),
                        minimo_noches_temporada_baja=hotel_data['politicas'].get('minimo_noches_baja', 1),
                        minimo_noches_temporada_alta=hotel_data['politicas'].get('minimo_noches_alta', 2),
                    )
                    hoteles_creados += 1
                    
                    # Agrupar tarifas por tipo de habitacion
                    tipos_habitacion = {}
                    for tarifa_data in hotel_data['tarifas']:
                        tipo_hab_nombre = tarifa_data['tipo_habitacion']
                        
                        # Crear tipo de habitacion si no existe
                        if tipo_hab_nombre not in tipos_habitacion:
                            tipo_hab = TipoHabitacion.objects.create(
                                hotel=hotel,
                                nombre=tipo_hab_nombre,
                                capacidad_adultos=2,
                                capacidad_ninos=0,
                                capacidad_total=2
                            )
                            tipos_habitacion[tipo_hab_nombre] = tipo_hab
                            tipos_hab_creados += 1
                        else:
                            tipo_hab = tipos_habitacion[tipo_hab_nombre]
                        
                        # Crear tarifa
                        TarifaHabitacion.objects.create(
                            tipo_habitacion=tipo_hab,
                            fecha_inicio=tarifa_data['fecha_inicio'],
                            fecha_fin=tarifa_data['fecha_fin'],
                            nombre_temporada=tarifa_data.get('temporada', ''),
                            moneda=tarifa_data.get('moneda', 'USD'),
                            tarifa_sgl=tarifa_data.get('tarifa_sgl'),
                            tarifa_dbl=tarifa_data.get('tarifa_dbl'),
                            tarifa_tpl=tarifa_data.get('tarifa_tpl'),
                            tarifa_cdp=tarifa_data.get('tarifa_cdp'),
                            tarifa_qpl=tarifa_data.get('tarifa_qpl'),
                            tarifa_sex_pax=tarifa_data.get('tarifa_sex_pax'),
                            tarifa_pax_adicional=tarifa_data.get('tarifa_pax_adicional'),
                            tarifa_nino_4_10=tarifa_data.get('tarifa_nino_4_10'),
                        )
                        tarifas_creadas += 1
                    
                    self.stdout.write(f'  [OK] {hotel.nombre} ({len(hotel_data["tarifas"])} tarifas)')
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  [ERROR] {hotel_data["nombre"]}: {str(e)[:100]}'))
                continue
        
        # Resumen
        self.stdout.write(self.style.SUCCESS('\n=== IMPORTACION COMPLETADA ==='))
        self.stdout.write(f'Hoteles creados: {hoteles_creados}')
        self.stdout.write(f'Tipos de habitacion: {tipos_hab_creados}')
        self.stdout.write(f'Tarifas creadas: {tarifas_creadas}')

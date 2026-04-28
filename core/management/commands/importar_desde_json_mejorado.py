from django.core.management.base import BaseCommand
from core.models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion
from core.models_catalogos import Proveedor
from datetime import datetime
from decimal import Decimal
import json
import re


class Command(BaseCommand):
    help = 'Importa hoteles desde JSON estructurado del PDF'

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
            nombre="Tarifario Nacional Septiembre 2025",
            defaults={
                'fecha_vigencia_inicio': datetime(2025, 9, 21).date(),
                'fecha_vigencia_fin': datetime(2026, 1, 15).date(),
                'comision_estandar': Decimal('15.00')
            }
        )

        hoteles_creados = 0
        tarifas_creadas = 0

        # Procesar cada página
        for pagina in data:
            if not pagina.get('tablas_extraidas'):
                continue
            
            # Buscar nombre del hotel en texto_plano
            texto = pagina.get('texto_plano', '')
            hotel_info = self._extraer_hotel_de_texto(texto)
            
            if not hotel_info:
                continue
            
            # Procesar tablas de tarifas
            for tabla in pagina['tablas_extraidas']:
                if not tabla or len(tabla) < 2:
                    continue
                
                # Detectar si es tabla de tarifas
                headers = tabla[0]
                if not self._es_tabla_tarifas(headers):
                    continue
                
                # Crear hotel
                hotel, created = HotelTarifario.objects.get_or_create(
                    tarifario=tarifario,
                    nombre=hotel_info['nombre'],
                    defaults={
                        'destino': hotel_info.get('destino', ''),
                        'regimen': hotel_info.get('regimen', 'SD'),
                        'comision': Decimal(hotel_info.get('comision', '15.00')),
                        'politicas': hotel_info.get('politicas', '')
                    }
                )
                
                if created:
                    hoteles_creados += 1
                    self.stdout.write(f"Hotel creado: {hotel.nombre}")
                
                # Procesar filas de tarifas
                for fila in tabla[1:]:
                    if not fila or len(fila) < 3:
                        continue
                    
                    tarifa_data = self._procesar_fila_tarifa(fila, headers)
                    if tarifa_data:
                        # Crear tipo de habitación
                        tipo_hab, _ = TipoHabitacion.objects.get_or_create(
                            hotel=hotel,
                            nombre=tarifa_data['tipo_habitacion'],
                            defaults={
                                'capacidad_adultos': 2,
                                'capacidad_ninos': 0,
                                'capacidad_total': 2
                            }
                        )
                        
                        # Crear tarifa
                        TarifaHabitacion.objects.get_or_create(
                            tipo_habitacion=tipo_hab,
                            fecha_inicio=tarifa_data['fecha_inicio'],
                            fecha_fin=tarifa_data['fecha_fin'],
                            defaults={
                                'nombre_temporada': tarifa_data.get('temporada', ''),
                                'moneda': tarifa_data.get('moneda', 'USD'),
                                'tipo_tarifa': tarifa_data.get('tipo_tarifa', 'POR_PERSONA'),
                                'tarifa_sgl': tarifa_data.get('sgl'),
                                'tarifa_dbl': tarifa_data.get('dbl'),
                                'tarifa_tpl': tarifa_data.get('tpl')
                            }
                        )
                        tarifas_creadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'Importacion completa: {hoteles_creados} hoteles, {tarifas_creadas} tarifas'
        ))

    def _extraer_hotel_de_texto(self, texto):
        """Extrae información del hotel del texto"""
        lineas = texto.split('\n')
        if len(lineas) < 2:
            return None
        
        nombre = lineas[0].strip()
        plan = lineas[1].strip() if len(lineas) > 1 else ''
        
        # Detectar régimen
        regimen_map = {
            'SOLO DESAYUNO': 'SD',
            'MEDIA PENSION': 'MP',
            'FULL PENSION': 'PC',
            'PENSION COMPLETA': 'PC',
            'TODO INCLUIDO': 'TI'
        }
        regimen = 'SD'
        for key, val in regimen_map.items():
            if key in plan.upper():
                regimen = val
                break
        
        # Extraer comisión
        match_comision = re.search(r'COMISIONABLE AL (\d+)%', texto)
        comision = match_comision.group(1) if match_comision else '15'
        
        # Extraer políticas
        politicas = ''
        if 'POLITICA' in texto:
            match_pol = re.search(r'POLITICA[^.]+\.', texto)
            if match_pol:
                politicas = match_pol.group(0)
        
        return {
            'nombre': nombre,
            'destino': '',  # Se puede extraer del JSON padre
            'regimen': regimen,
            'comision': comision,
            'politicas': politicas
        }

    def _es_tabla_tarifas(self, headers):
        """Detecta si una tabla contiene tarifas"""
        if not headers:
            return False
        
        headers_str = ' '.join(str(h).upper() for h in headers if h)
        keywords = ['SGL', 'DBL', 'VIGENCIA', 'TIPO DE HABITACION', 'HABITACIÓN']
        return any(kw in headers_str for kw in keywords)

    def _procesar_fila_tarifa(self, fila, headers):
        """Procesa una fila de tarifa"""
        if not fila or len(fila) < 3:
            return None
        
        # Buscar fechas en primera columna
        vigencia = str(fila[0]) if fila[0] else ''
        match_fechas = re.search(r'(\d{2}/\d{2}/\d{4})\s+AL\s+(\d{2}/\d{2}/\d{4})', vigencia)
        
        if not match_fechas:
            return None
        
        fecha_inicio = datetime.strptime(match_fechas.group(1), '%d/%m/%Y').date()
        fecha_fin = datetime.strptime(match_fechas.group(2), '%d/%m/%Y').date()
        
        # Tipo de habitación (segunda columna)
        tipo_hab = str(fila[1]).strip() if len(fila) > 1 and fila[1] else 'STANDARD'
        
        # Extraer tarifas
        sgl = self._parse_precio(fila[2]) if len(fila) > 2 else None
        dbl = self._parse_precio(fila[3]) if len(fila) > 3 else None
        tpl = self._parse_precio(fila[4]) if len(fila) > 4 else None
        
        # Detectar moneda
        moneda = 'USD'
        for val in fila:
            if val and '€' in str(val):
                moneda = 'EUR'
                break
        
        # Detectar temporada
        temporada = ''
        if 'NAVIDAD' in vigencia.upper():
            temporada = 'NAVIDAD'
        elif 'FIN DE AÑO' in vigencia.upper() or 'AÑO NUEVO' in vigencia.upper():
            temporada = 'FIN DE AÑO'
        elif 'TEMPORADA BAJA' in vigencia.upper():
            temporada = 'TEMPORADA BAJA'
        
        return {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'tipo_habitacion': tipo_hab,
            'temporada': temporada,
            'moneda': moneda,
            'tipo_tarifa': 'POR_PERSONA',
            'sgl': sgl,
            'dbl': dbl,
            'tpl': tpl
        }

    def _parse_precio(self, value):
        """Convierte string de precio a Decimal"""
        if not value or value == 'N/A':
            return None
        
        # Limpiar string
        precio_str = str(value).replace('$', '').replace('€', '').replace(',', '').strip()
        
        try:
            return Decimal(precio_str)
        except:
            return None

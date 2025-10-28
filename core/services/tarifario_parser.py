import PyPDF2
import re
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class TarifarioParser:
    """Parser para extraer datos de tarifarios de hoteles en PDF"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))
        self.destino_actual = None
    
    def extraer_hoteles(self):
        """Extrae todos los hoteles del PDF"""
        hoteles = []
        
        for i, page in enumerate(self.reader.pages):
            texto = page.extract_text()
            
            # Detectar cambio de destino
            self._detectar_destino(texto)
            
            # Detectar hotel
            if 'TARIFA COMISIONABLE' in texto or 'COMISIONABLE AL' in texto or 'AGENCIAS COMISIONABLE' in texto:
                hotel = self._parsear_hotel(texto)
                if hotel:
                    hoteles.append(hotel)
                    logger.info(f"Hotel extraído: {hotel['nombre']} - {hotel['destino']}")
        
        logger.info(f"Total de hoteles extraídos: {len(hoteles)}")
        return hoteles
    
    def _detectar_destino(self, texto):
        """Detecta el destino actual en el texto"""
        # Orden de prioridad para evitar falsos positivos
        if 'ISLA MARGARITA' in texto or 'ISLA DE MARGARITA' in texto:
            self.destino_actual = 'Isla Margarita'
        elif 'LOS ROQUES' in texto or 'ARCHIPIELAGO LOS ROQUES' in texto:
            self.destino_actual = 'Los Roques'
        elif 'MÉRIDA' in texto or 'MERIDA' in texto:
            self.destino_actual = 'Mérida'
        elif 'CANAIMA' in texto:
            self.destino_actual = 'Canaima'
        elif 'MORROCOY' in texto:
            self.destino_actual = 'Morrocoy'
        elif 'CARACAS' in texto:
            self.destino_actual = 'Caracas'
        elif 'MAIQUETIA' in texto or 'MAIQUETÍA' in texto:
            self.destino_actual = 'Maiquetia'
    
    def _parsear_hotel(self, texto):
        """Parsea un hotel individual"""
        try:
            # Extraer nombre del hotel
            nombre = None
            
            # Buscar nombres comunes de hoteles/posadas
            patrones_nombres = [
                r'(PARADISE [A-ZÁÉÍÓÚÑ]+)',
                r'(PARAISO [A-ZÁÉÍÓÚÑ]+)',
                r'(POSADA [A-ZÁÉÍÓÚÑ\s]+)',
                r'(HOTEL [A-ZÁÉÍÓÚÑ\s]+)',
                r'(HESPERIA [A-ZÁÉÍÓÚÑ]+)',
                r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,50})\s+(SOLO DESAYUNO|TODO INCLUIDO|MEDIA PENSIÓN|PENSIÓN COMPLETA|SOLO ALOJAMIENTO|FULL PENSIÓN)'
            ]
            
            for patron in patrones_nombres:
                match = re.search(patron, texto)
                if match:
                    nombre_candidato = match.group(1).strip()
                    # Filtrar inválidos
                    if ('WWW' not in nombre_candidato and 'TARIFA' not in nombre_candidato and 
                        'COMISIONABLE' not in nombre_candidato and 'VIGENCIA' not in nombre_candidato and
                        len(nombre_candidato) > 3):
                        nombre = nombre_candidato
                        break
            
            if not nombre:
                return None
            
            # Extraer régimen
            regimen = self._extraer_regimen(texto)
            
            # Extraer comisión
            comision = self._extraer_comision(texto)
            
            # Extraer ubicación
            ubicacion = self._extraer_ubicacion(texto)
            
            # Extraer políticas
            politicas = self._extraer_politicas(texto)
            
            # Extraer tarifas
            tarifas = self._extraer_tarifas(texto)
            
            return {
                'nombre': nombre,
                'destino': self.destino_actual or 'Sin Destino',
                'regimen': regimen,
                'comision': comision,
                'ubicacion': ubicacion,
                'politicas': politicas,
                'tarifas': tarifas
            }
        except Exception as e:
            logger.error(f"Error parseando hotel: {e}")
            return None
    
    def _extraer_regimen(self, texto):
        """Extrae el régimen alimenticio"""
        regimenes = {
            'SOLO DESAYUNO': 'SD',
            'TODO INCLUIDO': 'TI',
            'MEDIA PENSIÓN': 'MP',
            'PENSIÓN COMPLETA': 'PC',
            'FULL PENSIÓN': 'PC',
            'SOLO ALOJAMIENTO': 'SO',
        }
        
        for key, value in regimenes.items():
            if key in texto:
                return value
        
        return 'SD'  # Default
    
    def _extraer_comision(self, texto):
        """Extrae el porcentaje de comisión"""
        match = re.search(r'COMISIONABLE AL (\d+)%', texto)
        if match:
            return Decimal(match.group(1))
        # Buscar también "AGENCIAS COMISIONABLE"
        match = re.search(r'AGENCIAS COMISIONABLE AL (\d+)%', texto)
        if match:
            return Decimal(match.group(1))
        return Decimal('15.00')  # Default
    
    def _extraer_ubicacion(self, texto):
        """Extrae la descripción de ubicación"""
        # Buscar texto entre régimen y VIGENCIA
        match = re.search(r'(SOLO DESAYUNO|TODO INCLUIDO|MEDIA PENSIÓN|PENSIÓN COMPLETA|SOLO ALOJAMIENTO)\s+(.*?)\s+VIGENCIA', texto, re.DOTALL)
        if match:
            ubicacion = match.group(2).strip()
            # Limpiar
            ubicacion = re.sub(r'\s+', ' ', ubicacion)
            return ubicacion[:500]  # Limitar longitud
        return ''
    
    def _extraer_politicas(self, texto):
        """Extrae políticas del hotel"""
        politicas = {
            'ninos': '',
            'check_in': '15:00',
            'check_out': '12:00',
            'minimo_noches_baja': 1,
            'minimo_noches_alta': 2,
        }
        
        # Política de niños
        match = re.search(r'POLÍTICA DE NIÑOS:(.*?)(?:CHECK IN|$)', texto, re.DOTALL | re.IGNORECASE)
        if match:
            politicas['ninos'] = match.group(1).strip()[:500]
        
        # Check-in
        match = re.search(r'CHECK IN:\s*(\d{1,2}):(\d{2})', texto)
        if match:
            politicas['check_in'] = f"{match.group(1).zfill(2)}:{match.group(2)}"
        
        # Check-out
        match = re.search(r'CHECK OUT:\s*(\d{1,2}):(\d{2})', texto)
        if match:
            politicas['check_out'] = f"{match.group(1).zfill(2)}:{match.group(2)}"
        
        # Mínimo de noches
        match = re.search(r'MINIMO DE NOCHES:.*?(\d+)\s*NOCHES', texto, re.IGNORECASE)
        if match:
            politicas['minimo_noches_baja'] = int(match.group(1))
        
        return politicas
    
    def _extraer_tarifas(self, texto):
        """Extrae tabla de tarifas"""
        tarifas = []
        temporada_actual = ''
        
        # Detectar temporadas
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            # Detectar temporada
            if 'TEMPORADA BAJA' in linea or 'NAVIDAD' in linea or 'FIN DE AÑO' in linea:
                if 'TEMPORADA BAJA' in linea:
                    temporada_actual = 'TEMPORADA BAJA'
                elif 'NAVIDAD' in linea:
                    temporada_actual = 'NAVIDAD'
                elif 'FIN DE AÑO' in linea:
                    temporada_actual = 'FIN DE AÑO'
            
            # Buscar líneas con fechas y tarifas (USD o EUR)
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s*AL\s*(\d{2}/\d{2}/\d{4})([A-Z\s\(\)]+?)(\$|€)([\d,]+)\s+(\$|€)([\d,]+)\s+(\$|€)([\d,]+)\s+(\$[\d,]+|€[\d,]+|N/A)\s+(\$|€)([\d,]+)', linea)
            if match:
                try:
                    fecha_inicio = datetime.strptime(match.group(1), '%d/%m/%Y').date()
                    fecha_fin = datetime.strptime(match.group(2), '%d/%m/%Y').date()
                    tipo_hab = match.group(3).strip()
                    moneda = 'EUR' if '€' in match.group(4) else 'USD'
                    
                    tarifas.append({
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin,
                        'tipo_habitacion': tipo_hab,
                        'temporada': temporada_actual,
                        'moneda': moneda,
                        'tarifa_sgl': self._parse_precio(match.group(5)),
                        'tarifa_dbl': self._parse_precio(match.group(7)),
                        'tarifa_tpl': self._parse_precio(match.group(9)),
                        'tarifa_cdp': self._parse_precio(match.group(10)),
                        'tarifa_nino_4_10': self._parse_precio(match.group(11)),
                    })
                except Exception as e:
                    logger.warning(f"Error parseando tarifa: {e}")
        
        return tarifas
    
    def _parse_precio(self, precio_str):
        """Convierte string de precio a Decimal"""
        if not precio_str or precio_str.strip() == 'N/A':
            return None
        try:
            return Decimal(precio_str.replace(',', '').replace('$', '').replace('€', '').strip())
        except:
            return None

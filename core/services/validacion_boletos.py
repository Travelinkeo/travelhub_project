"""
Sistema de validación de boletos antes de enviar al cliente
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class ValidadorBoleto:
    """Valida boletos antes de enviar al cliente"""
    
    def __init__(self, boleto):
        self.boleto = boleto
        self.errores = []
        self.advertencias = []
    
    def validar_todo(self):
        """Ejecuta todas las validaciones"""
        self.validar_fechas()
        self.validar_ruta()
        self.validar_pasajero()
        self.validar_precio()
        self.validar_aerolinea()
        
        return {
            'valido': len(self.errores) == 0,
            'errores': self.errores,
            'advertencias': self.advertencias
        }
    
    def validar_fechas(self):
        """Valida que las fechas sean coherentes"""
        if not self.boleto.fecha_emision_boleto:
            self.advertencias.append("Fecha de emisión no disponible")
            return
        
        # Fecha de emisión no puede ser futura
        if self.boleto.fecha_emision_boleto > datetime.now().date():
            self.errores.append(f"Fecha de emisión es futura: {self.boleto.fecha_emision_boleto}")
        
        # Fecha de emisión no puede ser muy antigua (>2 años)
        hace_dos_anios = datetime.now().date() - timedelta(days=730)
        if self.boleto.fecha_emision_boleto < hace_dos_anios:
            self.advertencias.append(f"Boleto emitido hace más de 2 años: {self.boleto.fecha_emision_boleto}")
        
        # Validar fechas de vuelos
        datos = self.boleto.datos_parseados.get('normalized', {}) if self.boleto.datos_parseados else {}
        vuelos = datos.get('flights', [])
        
        for i, vuelo in enumerate(vuelos):
            fecha_str = vuelo.get('date')
            if fecha_str:
                try:
                    # Intentar parsear fecha
                    fecha_vuelo = datetime.strptime(fecha_str, '%d%b%y').date()
                    
                    # Vuelo no puede ser en el pasado (más de 1 día)
                    if fecha_vuelo < datetime.now().date() - timedelta(days=1):
                        self.advertencias.append(f"Vuelo {i+1} ya pasó: {fecha_str}")
                    
                    # Vuelo no puede ser muy lejano (>1 año)
                    en_un_anio = datetime.now().date() + timedelta(days=365)
                    if fecha_vuelo > en_un_anio:
                        self.advertencias.append(f"Vuelo {i+1} es en más de 1 año: {fecha_str}")
                
                except:
                    pass
    
    def validar_ruta(self):
        """Valida que la ruta sea lógica"""
        datos = self.boleto.datos_parseados.get('normalized', {}) if self.boleto.datos_parseados else {}
        vuelos = datos.get('flights', [])
        
        if not vuelos:
            self.advertencias.append("No se encontraron vuelos en el boleto")
            return
        
        for i, vuelo in enumerate(vuelos):
            origen = vuelo.get('origin', '').strip()
            destino = vuelo.get('destination', '').strip()
            
            # Origen y destino no pueden ser iguales
            if origen and destino and origen == destino:
                self.errores.append(f"Vuelo {i+1}: Origen y destino son iguales ({origen})")
            
            # Validar códigos IATA (3 letras)
            if origen and len(origen) != 3:
                self.advertencias.append(f"Vuelo {i+1}: Código de origen inválido ({origen})")
            
            if destino and len(destino) != 3:
                self.advertencias.append(f"Vuelo {i+1}: Código de destino inválido ({destino})")
    
    def validar_pasajero(self):
        """Valida datos del pasajero"""
        if not self.boleto.nombre_pasajero_procesado and not self.boleto.nombre_pasajero_completo:
            self.errores.append("Nombre del pasajero no disponible")
            return
        
        nombre = self.boleto.nombre_pasajero_procesado or self.boleto.nombre_pasajero_completo
        
        # Nombre muy corto
        if len(nombre) < 3:
            self.advertencias.append(f"Nombre del pasajero muy corto: {nombre}")
        
        # Validar documento
        if not self.boleto.foid_pasajero:
            self.advertencias.append("Documento de identidad del pasajero no disponible")
    
    def validar_precio(self):
        """Valida que el precio sea razonable"""
        if not self.boleto.total_boleto:
            self.advertencias.append("Precio total no disponible")
            return
        
        total = self.boleto.total_boleto
        
        # Precio negativo
        if total < 0:
            self.errores.append(f"Precio negativo: {total}")
        
        # Precio sospechosamente bajo (<$10)
        if 0 < total < Decimal('10.00'):
            self.advertencias.append(f"Precio muy bajo: ${total}")
        
        # Precio sospechosamente alto (>$10,000)
        if total > Decimal('10000.00'):
            self.advertencias.append(f"Precio muy alto: ${total}")
    
    def validar_aerolinea(self):
        """Valida que la aerolínea esté identificada"""
        if not self.boleto.aerolinea_emisora:
            self.advertencias.append("Aerolínea emisora no identificada")
            return
        
        # Lista de aerolíneas conocidas (puedes expandir)
        aerolineas_conocidas = [
            'AVIOR', 'CONVIASA', 'LASER', 'COPA', 'AVIANCA', 'LATAM',
            'AMERICAN', 'UNITED', 'DELTA', 'IBERIA', 'AIR EUROPA',
            'TURKISH', 'WINGO', 'ESTELAR'
        ]
        
        aerolinea_upper = self.boleto.aerolinea_emisora.upper()
        es_conocida = any(conocida in aerolinea_upper for conocida in aerolineas_conocidas)
        
        if not es_conocida:
            self.advertencias.append(f"Aerolínea no reconocida: {self.boleto.aerolinea_emisora}")


def validar_boleto(boleto):
    """
    Función helper para validar un boleto
    
    Returns:
        dict: {
            'valido': bool,
            'errores': list,
            'advertencias': list
        }
    """
    validador = ValidadorBoleto(boleto)
    return validador.validar_todo()

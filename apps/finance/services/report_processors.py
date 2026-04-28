import pandas as pd
from abc import ABC, abstractmethod
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class BaseReportProcessor(ABC):
    """
    Clase base para procesar archivos de reportes de proveedores.
    """
    @abstractmethod
    def parse(self, file_path):
        """
        Debe devolver una lista de diccionarios normalizados.
        Ejemplo: [{'numero_boleto': '123', 'monto_total': 100.0, 'pnr': 'ABCDEF', ...}]
        """
        pass

class KIUReportProcessor(BaseReportProcessor):
    """
    Procesador para reportes de KIU (CSV/Excel).
    """
    def parse(self, file_path):
        try:
            # KIU suele exportar CSV o Excel. Intentamos ambos.
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            normalized_data = []
            for _, row in df.iterrows():
                # Mapeo de columnas (estos nombres pueden variar según la versión del reporte)
                # Se asume un formato estándar de KIU, pero debería ser configurable o detectado.
                data = {
                    'numero_boleto': str(row.get('Ticket Number', row.get('Boleto', ''))).strip(),
                    'pnr': str(row.get('PNR', row.get('Resloc', ''))).strip(),
                    'pasajero': str(row.get('Passenger', row.get('Pasajero', ''))).strip(),
                    'monto_total': Decimal(str(row.get('Total', 0))),
                    'fecha_emision': row.get('Date', row.get('Fecha', None)),
                    'moneda': str(row.get('Currency', row.get('Moneda', 'USD'))).strip(),
                }
                if data['numero_boleto']:
                    normalized_data.append(data)
            
            return normalized_data
        except Exception as e:
            logger.error(f"Error parseando reporte KIU: {e}")
            raise

class BSPReportProcessor(BaseReportProcessor):
    """
    Procesador para reportes BSP (IATA). 
    Suele ser un formato de texto fijo o CSV complejo.
    """
    def parse(self, file_path):
        # Implementación simplificada para el MVP
        try:
            df = pd.read_csv(file_path) # Asumiendo CSV para simplificar
            normalized_data = []
            for _, row in df.iterrows():
                data = {
                    'numero_boleto': str(row.get('Document Number', '')).strip(),
                    'pnr': str(row.get('Booking Ref', '')).strip(),
                    'pasajero': str(row.get('Passenger Name', '')).strip(),
                    'monto_total': Decimal(str(row.get('Total Amount', 0))),
                    'fecha_emision': row.get('Issue Date', None),
                    'moneda': str(row.get('Currency', 'USD')).strip(),
                }
                if data['numero_boleto']:
                    normalized_data.append(data)
            return normalized_data
        except Exception as e:
            logger.error(f"Error parseando reporte BSP: {e}")
            raise

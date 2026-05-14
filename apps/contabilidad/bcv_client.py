# contabilidad/bcv_client.py
"""
Cliente para obtener tasa de cambio oficial del BCV.
Utiliza el endpoint oficial JSON del BCV como fuente primaria con fallback a Base de Datos.
"""

import logging
import warnings
from datetime import date
from decimal import Decimal

import requests
from urllib3.exceptions import InsecureRequestWarning

# Suprimir warnings de SSL para BCV (Común en servidores gubernamentales)
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

logger = logging.getLogger(__name__)


class BCVClient:
    """Cliente para consultar tasa de cambio del BCV via API JSON"""
    
    # Endpoint oficial JSON identificado por el equipo de integración
    BCV_API_URL = "https://www.bcv.org.ve/c2/rest/tasas"
    TIMEOUT = 10  # segundos
    
    @staticmethod
    def obtener_tasa_actual() -> Decimal | None:
        """
        Obtiene la tasa de cambio USD/BSD actual desde el endpoint JSON del BCV.
        
        Returns:
            Decimal con la tasa o la última tasa guardada en DB si el API falla.
        """
        try:
            # 1. Intento de conexión al endpoint oficial
            logger.info(f"Consultando endpoint oficial BCV: {BCVClient.BCV_API_URL}")
            response = requests.get(
                BCVClient.BCV_API_URL,
                timeout=BCVClient.TIMEOUT,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TravelHub/1.1'},
                verify=False  # Bypass por certificados SSL auto-firmados o vencidos del ente
            )
            response.raise_for_status()
            data = response.json()
            
            # 2. Parsing de la respuesta JSON
            # La respuesta es una lista de objetos: [{"moneda": "Dólar", "valor": "36.23"}, ...]
            tasa_usd = None
            for item in data:
                moneda_nombre = item.get('moneda', '')
                if 'Dólar' in moneda_nombre or 'USD' in moneda_nombre.upper():
                    valor_str = str(item.get('valor', '0')).replace(',', '.')
                    tasa_usd = Decimal(valor_str).quantize(Decimal('0.0001'))
                    break
            
            if tasa_usd:
                logger.info(f"✅ Tasa oficial obtenida del API BCV: {tasa_usd} BSD/USD")
                return tasa_usd
            else:
                raise ValueError("Campo 'Dólar' no encontrado en el payload JSON")
                
        except Exception as e:
            # 3. Alerta y Fallback (Paso Crítico para Resiliencia)
            logger.error(f"⚠️ FALLO EN ENDPOINT BCV: {str(e)}. Activando fallback de base de datos.")
            
            try:
                from .models import TasaCambioBCV
                ultima_tasa = TasaCambioBCV.objects.order_by('-fecha', '-id_tasa').first()
                
                if ultima_tasa:
                    logger.warning(f"🔄 Usando tasa histórica como fallback: {ultima_tasa.tasa_bsd_por_usd} (Fecha: {ultima_tasa.fecha})")
                    return ultima_tasa.tasa_bsd_por_usd
            except Exception as db_err:
                logger.critical(f"❌ FALLO TOTAL: No se pudo recuperar tasa ni del API ni de la DB: {db_err}")
                
            return None
    
    @staticmethod
    def actualizar_tasa_db(tasa: Decimal | None = None, fuente: str = "BCV API Official") -> bool:
        """
        Actualiza la tasa en la base de datos central.
        """
        try:
            from .models import TasaCambioBCV
            
            if tasa is None:
                tasa = BCVClient.obtener_tasa_actual()
                if tasa is None:
                    return False
            
            hoy = date.today()
            
            tasa_obj, created = TasaCambioBCV.objects.update_or_create(
                fecha=hoy,
                defaults={
                    'tasa_bsd_por_usd': tasa,
                    'fuente': fuente
                }
            )
            
            accion = "creada" if created else "actualizada"
            logger.info(f"Tasa BCV {accion} en DB: {hoy} = {tasa} BSD/USD")
            
            return True
            
        except Exception as e:
            logger.error(f"Error guardando tasa en DB: {e}")
            return False

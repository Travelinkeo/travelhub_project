import logging
import warnings
from decimal import Decimal

import requests
import urllib3

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Official and Fallback API Configuration
BCV_API_URL = "https://www.bcv.org.ve/c2/rest/tasas"
DOLAR_API_URL = "https://ve.dolarapi.com/v1/dolares"

def _obtener_tasas_dolarapi():
    """Fallback usando DolarApi (ve.dolarapi.com)"""
    try:
        logger.info("Intentando fallback con DolarApi...")
        response = requests.get(DOLAR_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        tasas = {}
        for item in data:
            if item.get('fuente') == 'oficial':
                promedio = item.get('promedio')
                if promedio:
                    tasas['USD'] = Decimal(str(promedio))
                break
        return tasas
    except Exception as e:
        logger.error(f"Error en fallback DolarApi: {e}")
        return {}

def obtener_tasas_bcv():
    """
    Obtiene las tasas de cambio del Banco Central de Venezuela.
    Utiliza el endpoint JSON oficial como fuente primaria.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TravelHub/1.1'
    }
    
    tasas = {}
    
    try:
        # Intento primario: Endpoint JSON Oficial
        logger.info(f"Consultando endpoint oficial BCV: {BCV_API_URL}")
        response = requests.get(BCV_API_URL, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Mapeo de nombres en el JSON del BCV a códigos ISO
        monedas_map = {
            'Dólar': 'USD',
            'Euro': 'EUR',
            'Yuan': 'CNY',
            'Lira': 'TRY',
            'Rublo': 'RUB'
        }
        
        for item in data:
            nombre = item.get('moneda', '')
            for bcv_name, iso in monedas_map.items():
                if bcv_name in nombre:
                    valor_str = str(item.get('valor', '0')).replace(',', '.')
                    tasas[iso] = Decimal(valor_str).quantize(Decimal('0.0001'))
        
        if tasas:
            logger.info(f"Tasas obtenidas exitosamente del API BCV: {list(tasas.keys())}")
            return tasas

    except Exception as e:
        logger.error(f"Error al consultar endpoint oficial del BCV: {e}. Intentando fallback...")
    
    # Fallback si el API oficial falla
    tasas = _obtener_tasas_dolarapi()
    
    if not tasas:
        logger.error("TODOS los métodos de obtención de tasas fallaron.")
        
    return tasas

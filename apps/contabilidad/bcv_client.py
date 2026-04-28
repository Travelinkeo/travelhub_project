# contabilidad/bcv_client.py
"""
Cliente para obtener tasa de cambio oficial del BCV.
Implementa scraping de la página web del BCV como fuente primaria.
"""

import logging
import re
import warnings
from decimal import Decimal
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

# Suprimir warnings de SSL para BCV
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

logger = logging.getLogger(__name__)


class BCVClient:
    """Cliente para consultar tasa de cambio del BCV"""
    
    BCV_URL = "https://www.bcv.org.ve/"
    TIMEOUT = 10  # segundos
    
    @staticmethod
    def obtener_tasa_actual() -> Optional[Decimal]:
        """
        Obtiene la tasa de cambio USD/BSD actual desde el sitio web del BCV.
        
        Returns:
            Decimal con la tasa o None si falla
        """
        try:
            response = requests.get(
                BCVClient.BCV_URL,
                timeout=BCVClient.TIMEOUT,
                headers={'User-Agent': 'Mozilla/5.0'},
                verify=False  # BCV tiene problemas de certificado SSL
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar el div con id "dolar"
            dolar_div = soup.find('div', {'id': 'dolar'})
            if not dolar_div:
                logger.error("No se encontró div#dolar en página BCV")
                return None
            
            # Buscar strong con la tasa
            strong = dolar_div.find('strong')
            if not strong:
                logger.error("No se encontró elemento strong en div#dolar")
                return None
            
            # Extraer texto y limpiar
            texto = strong.get_text(strip=True)
            
            # Remover comas y convertir
            texto_limpio = texto.replace(',', '.')
            
            # Extraer número usando regex
            match = re.search(r'(\d+[.,]\d+)', texto_limpio)
            if not match:
                logger.error(f"No se pudo extraer número de: {texto}")
                return None
            
            tasa = Decimal(match.group(1).replace(',', '.'))
            
            # Redondear a 4 decimales (límite del modelo)
            tasa = tasa.quantize(Decimal('0.0001'))
            
            logger.info(f"Tasa BCV obtenida: {tasa} BSD/USD")
            return tasa
            
        except requests.RequestException as e:
            logger.error(f"Error HTTP consultando BCV: {e}")
            return None
        except Exception as e:
            logger.error(f"Error procesando respuesta BCV: {e}")
            return None
    
    @staticmethod
    def actualizar_tasa_db(tasa: Optional[Decimal] = None, fuente: str = "BCV Web") -> bool:
        """
        Actualiza la tasa en la base de datos.
        Si no se proporciona tasa, la obtiene automáticamente.
        
        Args:
            tasa: Tasa a guardar (opcional, se obtiene si es None)
            fuente: Descripción de la fuente
            
        Returns:
            True si se actualizó correctamente
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
            logger.info(f"Tasa BCV {accion}: {hoy} = {tasa} BSD/USD")
            
            return True
            
        except Exception as e:
            logger.error(f"Error guardando tasa en DB: {e}")
            return False

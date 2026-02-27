import requests
from bs4 import BeautifulSoup
from decimal import Decimal
import logging
import urllib3

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

def obtener_tasas_bcv():
    """
    Obtiene las tasas de cambio del Banco Central de Venezuela.
    Retorna un diccionario con las tasas: {'USD': Decimal('...'), 'EUR': Decimal('...')}
    """
    url = "http://www.bcv.org.ve/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    tasas = {}
    
    try:
        # BCV suele tener problemas de SSL, verify=False es necesario a veces
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # El BCV suele poner las tasas en un div con id o clase especifica, 
        # pero a veces cambia. Buscamos por el texto de la moneda.
        
        # Buscar el contenedor del Dolar
        # Usualmente es <div id="dolar"> o similar, dentro hay un strong con la tasa
        
        # Estrategia 1: Buscar por ID comunes
        monedas_map = {
            'dolar': 'USD',
            'euro': 'EUR'
        }
        
        for div_id, codigo_iso in monedas_map.items():
            contenedor = soup.find(id=div_id)
            if contenedor:
                # Buscar el valor numérico dentro
                # Normalmente está en un <strong> o directo en el texto
                texto_tasa = contenedor.get_text(strip=True)
                
                # Limpiar texto: buscar patrón numérico "00,00000000"
                # Extraer solo digitos y coma
                import re
                match = re.search(r'(\d+,\d+)', texto_tasa)
                if match:
                    valor_str = match.group(1).replace(',', '.')
                    tasas[codigo_iso] = Decimal(valor_str)
                    logger.info(f"Tasa {codigo_iso} encontrada: {tasas[codigo_iso]}")
        
        # Estrategia 2: Si falla ID, buscar por texto visible cerca
        if 'USD' not in tasas or 'EUR' not in tasas:
             # Buscar recuadros que contengan "USD" o "EUR"
             target_texts = {'USD': 'USD', 'EUR': 'EUR', 'CNY': 'CNY', 'TRY': 'TRY', 'RUB': 'RUB'}
             
             # Buscar en todos los divs que tengan clase "recuadrotsmc" o similar si existe
             # O simplemente buscar tags que contengan el texto
             for iso, search_text in target_texts.items():
                 if iso in tasas: continue
                 
                 found = soup.find(string=re.compile(search_text, re.IGNORECASE))
                 if found:
                     # Buscar el valor en el padre o hermanos
                     parent = found.parent
                     # Buscar el siguiente texto que parezca un número
                     # A veces está en un div hermano o un strong hijo del padre
                     # Buscamos en todo el contenedor abuelo (el recuadro)
                     container = parent.find_parent('div')
                     if container:
                         # Buscar numero
                         full_text = container.get_text(strip=True)
                         match = re.search(r'(\d+,\d+)', full_text)
                         if match:
                             valor_str = match.group(1).replace(',', '.')
                             tasas[iso] = Decimal(valor_str)
        
        if not tasas:
            logger.warning("No se pudieron extraer tasas del BCV.")
            
        return tasas

    except Exception as e:
        logger.error(f"Error extrayendo tasas BCV: {e}")
        return {}

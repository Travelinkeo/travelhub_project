# contabilidad/tasas_venezuela_client.py
"""
Cliente mejorado para obtener múltiples tasas de cambio de Venezuela:
- BCV (oficial)
- Promedio (mercado)
- P2P (peer-to-peer)
- Otras monedas (EUR, COP, etc.)
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TasasVenezuelaClient:
    """Cliente para obtener tasas de cambio de múltiples fuentes"""
    
    # API principal: DolarApi Venezuela (gratuita y confiable)
    API_URL = "https://ve.dolarapi.com/v1/dolares"
    TIMEOUT = 10
    
    @classmethod
    def obtener_todas_tasas(cls) -> Optional[Dict]:
        """
        Obtiene todas las tasas disponibles desde DolarApi Venezuela.
        
        Returns:
            Dict con estructura:
            {
                'oficial': {'price': Decimal, 'last_update': str, 'title': str},
                'paralelo': {'price': Decimal, 'last_update': str, 'title': str},
                'bitcoin': {'price': Decimal, 'last_update': str, 'title': str}
            }
        """
        try:
            logger.info(f"Consultando DolarApi Venezuela: {cls.API_URL}")
            response = requests.get(
                cls.API_URL,
                timeout=cls.TIMEOUT,
                headers={'User-Agent': 'TravelHub/1.0'}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Procesar datos de DolarApi
            tasas = {}
            
            # 1. Intentar obtener Tasa Oficial DIRECTAMENTE del BCV (Más precisa)
            try:
                from core.bcv_scraper import obtener_tasas_bcv
                tasas_bcv = obtener_tasas_bcv()
                if tasas_bcv:
                    if 'USD' in tasas_bcv:
                        tasas['oficial'] = {
                            'price': tasas_bcv['USD'].quantize(Decimal('0.0001')),
                            'last_update': datetime.now().isoformat(),
                            'title': 'BCV Oficial (Directo)',
                            'symbol': 'Bs.'
                        }
                    
                    if 'EUR' in tasas_bcv:
                        tasas['euro_bcv'] = {
                            'price': tasas_bcv['EUR'].quantize(Decimal('0.0001')),
                            'last_update': datetime.now().isoformat(),
                            'title': 'BCV Euro',
                            'symbol': 'Bs.'
                        }

            except Exception as e:
                logger.error(f"Falló scraper directo BCV: {e}")

            for item in data:
                try:
                    fuente = item.get('fuente', 'unknown')
                    
                    # Si ya tenemos oficial del scraper directo, saltar el de la API
                    if fuente == 'oficial' and 'oficial' in tasas:
                        continue
                        
                    promedio = item.get('promedio')
                    
                    if promedio and promedio > 0:
                        # Mapear nombres
                        nombre_map = {
                            'oficial': 'BCV Oficial',
                            'paralelo': 'Dólar No Oficial',
                            'bitcoin': 'Bitcoin'
                        }
                        
                        tasas[fuente] = {
                            'price': Decimal(str(promedio)).quantize(Decimal('0.01')),
                            'last_update': item.get('fechaActualizacion', ''),
                            'title': nombre_map.get(fuente, item.get('nombre', fuente)),
                            'symbol': 'Bs.'
                        }
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Error procesando item: {e}")
                    continue
            
            if tasas:
                logger.info(f"Tasas obtenidas: {len(tasas)} fuentes")
                return tasas
            else:
                logger.error("No se obtuvieron tasas válidas")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error HTTP consultando DolarApi: {e}")
            return None
        except Exception as e:
            logger.error(f"Error procesando respuesta: {e}")
            return None
    
    @classmethod
    def obtener_tasa_bcv(cls) -> Optional[Decimal]:
        """Obtiene solo la tasa BCV oficial"""
        tasas = cls.obtener_todas_tasas()
        if tasas and 'oficial' in tasas:
            return tasas['oficial']['price']
        return None
    
    @classmethod
    def obtener_tasa_paralelo(cls) -> Optional[Decimal]:
        """Obtiene la tasa del mercado paralelo"""
        tasas = cls.obtener_todas_tasas()
        if tasas and 'paralelo' in tasas:
            return tasas['paralelo']['price']
        return None
    
    @classmethod
    def obtener_tasa_bitcoin(cls) -> Optional[Decimal]:
        """Obtiene la tasa Bitcoin"""
        tasas = cls.obtener_todas_tasas()
        if tasas and 'bitcoin' in tasas:
            return tasas['bitcoin']['price']
        return None
    
    @classmethod
    def actualizar_tasas_db(cls) -> Dict[str, bool]:
        """
        Actualiza la tasa oficial (BCV) en la base de datos y TipoCambio (Core).
        
        Returns:
            Dict con resultados: {'oficial': True, 'paralelo': False, ...}
        """
        from .models import TasaCambioBCV
        from core.models_catalogos import TipoCambio, Moneda
        from datetime import date
        
        resultados = {}
        tasas = cls.obtener_todas_tasas()
        
        if not tasas:
            logger.error("No se pudieron obtener tasas")
            return resultados
        
        hoy = date.today()
        
        # 1. Actualizar tabla historica TasaCambioBCV (Solo USD)
        if 'oficial' in tasas:
            try:
                TasaCambioBCV.objects.update_or_create(
                    fecha=hoy,
                    defaults={
                        'tasa_bsd_por_usd': tasas['oficial']['price'],
                        'fuente': 'DolarApi - BCV Oficial'
                    }
                )
                resultados['oficial'] = True
                logger.info(f"Tasa BCV (USD) actualizada: {tasas['oficial']['price']}")
            except Exception as e:
                logger.error(f"Error guardando tasa BCV: {e}")
                resultados['oficial'] = False
        
        # 2. Actualizar tabla central TipoCambio (USD y EUR)
        # Buscar moneda destino (VES)
        moneda_ves = Moneda.objects.filter(codigo_iso='VES').first()
        
        if not moneda_ves:
             logger.error("No se encontró moneda VES para actualizar tasas.")
             return resultados

        # Mapeo de claves con Moneda Origen ISO
        mapa_monedas = {
            'oficial': 'USD',
            'euro_bcv': 'EUR'
        }

        for clave_tasa, codigo_iso_origen in mapa_monedas.items():
            if clave_tasa in tasas:
                try:
                    moneda_origen = Moneda.objects.filter(codigo_iso=codigo_iso_origen).first()
                    if moneda_origen:
                        valor_tasa = tasas[clave_tasa]['price']
                        
                        tipo_cambio, created = TipoCambio.objects.update_or_create(
                            moneda_origen=moneda_origen,
                            moneda_destino=moneda_ves,
                            fecha_efectiva=hoy,
                            defaults={
                                'tasa_conversion': valor_tasa
                            }
                        )
                        logger.info(f"TipoCambio {codigo_iso_origen}->VES actualizado: {valor_tasa}")
                except Exception as e:
                    logger.error(f"Error actualizando TipoCambio {codigo_iso_origen}: {e}")
        
        return resultados
    
    @classmethod
    def obtener_resumen_tasas(cls) -> Dict:
        """
        Obtiene un resumen de las tasas principales para mostrar en frontend.
        
        Returns:
            {
                'oficial': {'valor': Decimal, 'fecha': str, 'nombre': str},
                'paralelo': {'valor': Decimal, 'fecha': str, 'nombre': str},
                'bitcoin': {'valor': Decimal, 'fecha': str, 'nombre': str}
            }
        """
        tasas = cls.obtener_todas_tasas()
        resumen = {}
        
        if not tasas:
            return resumen
        
        # Oficial (BCV)
        if 'oficial' in tasas:
            resumen['oficial'] = {
                'valor': float(tasas['oficial']['price']),
                'fecha': tasas['oficial']['last_update'],
                'nombre': 'BCV Oficial'
            }
        
        # Paralelo (mostrar como "No Oficial")
        if 'paralelo' in tasas:
            resumen['paralelo'] = {
                'valor': float(tasas['paralelo']['price']),
                'fecha': tasas['paralelo']['last_update'],
                'nombre': 'Dólar No Oficial'
            }
        
        # Bitcoin
        if 'bitcoin' in tasas:
            resumen['bitcoin'] = {
                'valor': float(tasas['bitcoin']['price']),
                'fecha': tasas['bitcoin']['last_update'],
                'nombre': 'Bitcoin'
            }
        
        return resumen

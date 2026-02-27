import logging
from typing import Any, Dict, Optional
from zeep import Client, Settings, Plugin
from zeep.transports import Transport
from zeep.cache import SqliteCache
from requests import Session
import os

logger = logging.getLogger(__name__)

class SoapClient:
    """
    Cliente SOAP unificado para TravelHub (Wrapper sobre Zeep).
    Maneja la conexión, caché y autenticación para servicios legacy (KIU, Sabre XML).
    """

    def __init__(self, wsdl_url: str, service_name: str = "Unknown"):
        self.wsdl_url = wsdl_url
        self.service_name = service_name
        self.client = None
        self.transport = None
        self._initialize_client()

    def _initialize_client(self):
        """Inicializa el cliente Zeep con caché y transporte optimizado."""
        try:
            # 1. Configuración de Caché (Evita descargar el WSDL en cada petición)
            # Se guarda en la carpeta temporal del sistema o en una ruta específica
            cache_path = os.path.join(os.getcwd(), '.zeep_cache.db')
            cache = SqliteCache(path=cache_path, timeout=86400) # 24 horas

            # 2. Configuración de Transporte (Session keep-alive)
            session = Session()
            session.verify = True # Verificar SSL siempre en producción
            self.transport = Transport(cache=cache, session=session)

            # 3. Ajustes de Zeep
            settings = Settings(strict=False, xml_huge_tree=True)

            logger.info(f"Inicializando SOAP Client para {self.service_name}...")
            self.client = Client(
                wsdl=self.wsdl_url,
                transport=self.transport,
                settings=settings
            )
            logger.info(f"Cliente SOAP {self.service_name} listo.")

        except Exception as e:
            logger.error(f"Error fatal inicializando SoapClient ({self.service_name}): {e}")
            raise

    def call(self, method_name: str, **kwargs) -> Dict[str, Any]:
        """
        Método genérico para llamar a una función SOAP.
        
        Uso:
            client.call('AirAvail', Origin='CCS', Destination='MIA')
        """
        if not self.client:
            raise RuntimeError("El cliente SOAP no está inicializado.")

        try:
            # Obtener el método dinámicamente
            service_method = getattr(self.client.service, method_name, None)
            if not service_method:
                raise ValueError(f"El método {method_name} no existe en este servicio SOAP.")

            # Ejecutar la llamada
            logger.debug(f"Ejecutando SOAP {self.service_name}.{method_name} con args: {kwargs}")
            response = service_method(**kwargs)
            
            # Zeep devuelve objetos complejos, aquí podríamos convertirlos a Dict si fuera necesario
            # Por ahora retornamos el objeto raw para que el servicio específico lo procese
            return response

        except Exception as e:
            logger.error(f"Error ejecutando SOAP {method_name}: {e}")
            # Aquí podríamos lanzar una excepción personalizada de TravelHub
            raise e

# Ejemplo de uso (comentado):
# kiu_client = SoapClient('https://ssl.kiusys.com/ws3/index.php?wsdl', 'KIU')
# try:
#     res = kiu_client.call('AirAvail', Origin='CCS', Destination='MAD')
#     print(res)
# except Exception as e:
#     print(f"Fallo: {e}")

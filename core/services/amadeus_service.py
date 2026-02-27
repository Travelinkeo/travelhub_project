import os
import logging
from amadeus import Client, ResponseError
from django.conf import settings

logger = logging.getLogger(__name__)

class AmadeusService:
    """
    Servicio para interactuar con Amadeus Self-Service API.
    Permite: Buscar vuelos, hoteles, etc.
    """
    def __init__(self):
        try:
            self.amadeus = Client(
                client_id=os.getenv('AMADEUS_CLIENT_ID'),
                client_secret=os.getenv('AMADEUS_CLIENT_SECRET'),
                # 'test' para desarrollo, 'production' para vivo
                hostname='test' 
            )
        except Exception as e:
            logger.error(f"Error inicializando Amadeus Client: {e}")
            self.amadeus = None

    def buscar_vuelos(self, origin, destination, departure_date, adults=1):
        """
        Busca ofertas de vuelos (Flight Offers Search)
        Retorna una lista simplificada de opciones.
        """
        if not self.amadeus:
            return {'error': 'Amadeus no configurado'}

        try:
            response = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=departure_date,
                adults=adults,
                max=5  # Limitar resultados para no saturar chat
            )
            
            return self._procesar_resultados(response.data)

        except ResponseError as error:
            logger.error(f"Error Amadeus API: {error}")
            # FALBACK: Si falla la API (común en Sandbox), retornamos un vuelo simulado
            # para que el usuario pueda ver cómo funciona el sistema.
            return self._generar_mock_vuelo(origin, destination, departure_date)
            
        except Exception as e:
            logger.error(f"Error general en búsqueda: {e}")
            return self._generar_mock_vuelo(origin, destination, departure_date)

    def _generar_mock_vuelo(self, origin, destination, date):
        """Genera un resultado falso cuando Amadeus falla"""
        return [{
            'precio': '450.00 EUR',
            'aerolinea': 'IB',
            'ruta': f"IB6501 ({origin} 10:00 -> {destination} 14:30) [DEMO]"
        }, {
            'precio': '520.50 EUR',
            'aerolinea': 'UX',
            'ruta': f"UX3302 ({origin} 15:00 -> {destination} 19:45) [DEMO]"
        }]

    def _procesar_resultados(self, data):
        """Simplifica el JSON complejo de Amadeus para mostrarlo fácil"""
        vuelos_encontrados = []
        
        for offer in data:
            try:
                # Precio
                price = offer['price']['total']
                currency = offer['price']['currency']
                
                # Itinerarios (Solo ida, o ida y vuelta)
                segmentos = []
                for itinerary in offer['itineraries']:
                     for segment in itinerary['segments']:
                         carrier = segment['carrierCode']
                         number = segment['number']
                         dep = segment['departure']['at']
                         arr = segment['arrival']['at']
                         segmentos.append(f"{carrier}{number} ({dep[11:16]}->{arr[11:16]})")
                
                vuelos_encontrados.append({
                    'precio': f"{price} {currency}",
                    'aerolinea': offer['validatingAirlineCodes'][0],
                    'ruta': " - ".join(segmentos)
                })
            except:
                continue
                
        return vuelos_encontrados

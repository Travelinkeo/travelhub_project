import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from fli.search import SearchFlights
from fli.models import FlightSearchFilters, PassengerInfo, SeatType, MaxStops, SortBy, EmissionsFilter, Airport
from fli.core.builders import build_flight_segments

logger = logging.getLogger(__name__)

class FliFlightService:
    """
    Servicio premium que utiliza Google Flights (vía fli) para obtener
    disponibilidad y precios REALES. Reemplaza el sandbox limitado de Amadeus.
    """

    def buscar_vuelos(self, origin_code: str, destination_code: str, departure_date: str, 
                      return_date: str = None, multi_segments: list = None, adults: int = 1,
                      stops: str = 'ANY', airline_filter: str = None) -> List[Dict[str, Any]]:
        """
        Realiza la búsqueda en Google Flights y mapea los resultados al formato de TravelHub.
        Soporta filtros de escalas y aerolíneas por texto.
        """
        try:
            logger.info(f"🚀 Iniciando búsqueda REAL via Fli: Type={'MULTI' if multi_segments else ('ROUND' if return_date else 'ONE_WAY')}, Stops={stops}")
            
            from fli.models import TripType, FlightSegment, MaxStops
            
            # Mapeo de escalas
            stops_enum = getattr(MaxStops, stops, MaxStops.ANY)
            
            if multi_segments:
                trip_type = TripType.MULTI_CITY
                segments = []
                for seg in multi_segments:
                    origin = getattr(Airport, seg['origin'].upper())
                    dest = getattr(Airport, seg['destination'].upper())
                    segments.append(FlightSegment(
                        departure_airport=origin,
                        arrival_airport=dest,
                        departure_date=seg['date']
                    ))
            else:
                try:
                    origin = getattr(Airport, origin_code.upper())
                    destination = getattr(Airport, destination_code.upper())
                except AttributeError:
                    return [{"error": f"Código de aeropuerto no reconocido: {origin_code}/{destination_code}"}]

                segments, trip_type = build_flight_segments(
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date,
                    return_date=return_date
                )

            # 2. Configurar filtros
            filters = FlightSearchFilters(
                trip_type=trip_type,
                passenger_info=PassengerInfo(adults=adults),
                flight_segments=segments,
                stops=stops_enum,
                seat_type=SeatType.ECONOMY,
                sort_by=SortBy.BEST,
                emissions=EmissionsFilter.ALL
            )

            # 3. Ejecutar búsqueda
            engine = SearchFlights()
            # Nota: fli actualmente no tiene un parámetro directo expuesto para moneda en FlightSearchFilters,
            # pero suele retornar la moneda local o USD dependiendo del servidor.
            results = engine.search(filters=filters)

            if not results:
                logger.warning("No se encontraron vuelos en Google Flights para esta búsqueda.")
                return []

            # 4. Mapear resultados
            vuelos_procesados = []
            for res in results:
                if isinstance(res, (tuple, list)):
                    flight = res[0]
                    total_price = getattr(flight, 'price', 0)
                    currency = getattr(flight, 'currency', 'USD')
                else:
                    flight = res
                    total_price = flight.price
                    currency = flight.currency

                # Filtro por aerolínea manual si fli no lo soportó en el request
                leg = flight.legs[0]
                airline_name = leg.airline.name if hasattr(leg.airline, 'name') else "Desconocida"
                
                if airline_filter and airline_filter.lower() not in airline_name.lower() and airline_filter.upper() not in (leg.airline.value if hasattr(leg.airline, 'value') else ""):
                    continue

                vuelos_procesados.append({
                    'precio': f"{total_price} USD" if currency == 'USD' else f"{total_price} {currency} (Aprox USD)",
                    'aerolinea': leg.airline.value if hasattr(leg.airline, 'value') else "YY",
                    'aerolinea_nombre': airline_name,
                    'ruta': f"{leg.flight_number} ({leg.departure_airport.name} -> {leg.arrival_airport.name})",
                    'fecha': leg.departure_datetime.strftime('%d/%m/%Y %H:%M'),
                    'real': True,
                    'is_round_trip': trip_type == TripType.ROUND_TRIP,
                    'is_multi_city': trip_type == TripType.MULTI_CITY
                })
                
                if len(vuelos_procesados) >= 15: # Máximo 15 resultados filtrados
                    break

            return vuelos_procesados

        except Exception as e:
            logger.error(f"Error crítico en FliFlightService: {e}", exc_info=True)
            return [{"error": f"Error de conexión con el proveedor de búsqueda: {str(e)}"}]

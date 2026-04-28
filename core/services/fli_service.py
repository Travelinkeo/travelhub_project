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

            # 4. Obtener tasa de cambio una sola vez antes del bucle (Optimización)
            tasa_ves_usd = 0.0
            try:
                from core.services.bcv_service import obtener_tasa_bcv_resiliente
                tasa_ves_usd = obtener_tasa_bcv_resiliente('USD')
            except Exception as e:
                logger.warning(f"Error al pre-cargar tasa BCV: {e}")

            # 5. Mapear resultados
            vuelos_procesados = []
            for res in results:
                # fli retorna una tupla de vuelos para ROUND_TRIP o MULTI_CITY
                itinerario = list(res) if isinstance(res, (tuple, list)) else [res]
                
                if not itinerario:
                    continue

                # El precio suele estar en el primer objeto del itinerario o ser común
                first_f = itinerario[0]
                total_price = getattr(first_f, 'price', 0)
                currency = getattr(first_f, 'currency', 'USD')

                # Filtro por aerolínea basado en el primer tramo
                leg_principal = first_f.legs[0]
                airline_name = leg_principal.airline.name if hasattr(leg_principal.airline, 'name') else "Desconocida"
                
                if airline_filter and airline_filter.lower() not in airline_name.lower() and airline_filter.upper() not in (leg_principal.airline.value if hasattr(leg_principal.airline, 'value') else ""):
                    continue

                # Conversión de moneda optimizada
                display_price = f"{total_price} {currency}"
                if currency == 'VES' and tasa_ves_usd > 0:
                    precio_usd = round(total_price / tasa_ves_usd, 2)
                    display_price = f"{precio_usd} USD"
                elif currency == 'USD':
                    display_price = f"{total_price} USD"

                # Extraer TODOS los tramos de TODOS los vuelos del itinerario
                tramos_data = []
                for f_obj in itinerario:
                    for l in f_obj.legs:
                        tramos_data.append({
                            'vuelo': l.flight_number,
                            'aerolinea': l.airline.name if hasattr(l.airline, 'name') else "YY",
                            'origen': l.departure_airport.name,
                            'destino': l.arrival_airport.name,
                            'salida': l.departure_datetime.strftime('%d/%m/%Y %H:%M'),
                            'aerolinea_codigo': l.airline.value if hasattr(l.airline, 'value') else "YY"
                        })

                vuelos_procesados.append({
                    'precio': display_price,
                    'aerolinea': leg_principal.airline.value if hasattr(leg_principal.airline, 'value') else "YY",
                    'aerolinea_nombre': airline_name,
                    'tramos': tramos_data,
                    'ruta': f"{tramos_data[0]['origen']} -> {tramos_data[-1]['destino']}",
                    'fecha': tramos_data[0]['salida'].split(' ')[0],
                    'real': True,
                    'is_round_trip': trip_type == TripType.ROUND_TRIP,
                    'is_multi_city': trip_type == TripType.MULTI_CITY
                })
                
                if len(vuelos_procesados) >= 15:
                    break

            return vuelos_procesados

        except Exception as e:
            logger.error(f"Error crítico en FliFlightService: {e}", exc_info=True)
            return [{"error": f"Error de conexión con el proveedor de búsqueda: {str(e)}"}]

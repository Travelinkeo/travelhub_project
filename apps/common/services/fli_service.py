import logging
from decimal import Decimal
from typing import Any

from fli.core.builders import build_flight_segments
from fli.models import (
    Airport,
    EmissionsFilter,
    FlightSearchFilters,
    PassengerInfo,
    SeatType,
    SortBy,
)
from fli.search import SearchFlights

logger = logging.getLogger(__name__)


class FliFlightService:
    """
    Servicio premium que utiliza Google Flights (vía fli) para obtener
    disponibilidad y precios REALES. Reemplaza el sandbox limitado de Amadeus.
    """

    def buscar_vuelos(
        self,
        origin_code: str,
        destination_code: str,
        departure_date: str,
        return_date: str = None,
        multi_segments: list = None,
        adults: int = 1,
        stops: str = "ANY",
        airline_filter: str = None,
    ) -> list[dict[str, Any]]:
        """
        Realiza la búsqueda en Google Flights y mapea los resultados al formato de TravelHub.
        Soporta filtros de escalas y aerolíneas por texto.
        """
        try:
            logger.info(
                f"🚀 Iniciando búsqueda REAL via Fli: Type={'MULTI' if multi_segments else ('ROUND' if return_date else 'ONE_WAY')}, Stops={stops}"
            )

            from fli.models import FlightSegment, MaxStops, TripType

            # Mapeo de escalas
            stops_enum = getattr(MaxStops, stops, MaxStops.ANY)

            if multi_segments:
                trip_type = TripType.MULTI_CITY
                segments = []
                for seg in multi_segments:
                    origin = getattr(Airport, seg["origin"].upper())
                    dest = getattr(Airport, seg["destination"].upper())
                    segments.append(
                        FlightSegment(
                            departure_airport=origin,
                            arrival_airport=dest,
                            departure_date=seg["date"],
                        )
                    )
            else:
                try:
                    origin = getattr(Airport, origin_code.upper())
                    destination = getattr(Airport, destination_code.upper())
                except AttributeError:
                    return [
                        {
                            "error": f"Código de aeropuerto no reconocido: {origin_code}/{destination_code}"
                        }
                    ]

                segments, trip_type = build_flight_segments(
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date,
                    return_date=return_date,
                )

            # 2. Configurar filtros
            filters = FlightSearchFilters(
                trip_type=trip_type,
                passenger_info=PassengerInfo(adults=adults),
                flight_segments=segments,
                stops=stops_enum,
                seat_type=SeatType.ECONOMY,
                sort_by=SortBy.BEST,
                emissions=EmissionsFilter.ALL,
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
            tasa_ves_usd = Decimal("0")
            try:
                from django.utils.module_loading import import_string

                obtener_tasa_bcv_resiliente = import_string(
                    "apps.finance.services.bcv_service.obtener_tasa_bcv_resiliente"
                )
                tasa_ves_usd = obtener_tasa_bcv_resiliente("USD")
            except Exception as e:
                logger.warning(f"Error al pre-cargar tasa BCV: {e}")

            # 5. Mapear resultados con estructura profesional de trayectos
            vuelos_procesados = []
            for res in results:
                itinerario = list(res) if isinstance(res, tuple | list) else [res]
                if not itinerario:
                    continue

                first_f = itinerario[0]
                total_price = getattr(first_f, "price", 0)
                currency = getattr(first_f, "currency", "USD")

                # Primer tramo para información general de aerolínea
                first_leg_overall = first_f.legs[0] if first_f.legs else None
                if not first_leg_overall:
                    continue

                airline_name = (
                    first_leg_overall.airline.name
                    if hasattr(first_leg_overall.airline, "name")
                    else "Aerolínea"
                )
                airline_code = (
                    first_leg_overall.airline.value
                    if hasattr(first_leg_overall.airline, "value")
                    else "YY"
                )

                if (
                    airline_filter
                    and airline_filter.lower() not in airline_name.lower()
                    and airline_filter.upper() not in airline_code
                ):
                    continue

                # Conversión de moneda
                display_price = f"{total_price:,.2f} {currency}"
                precio_ves_str = None
                if currency == "USD" and tasa_ves_usd > 0:
                    try:
                        monto_ves = Decimal(str(total_price)) * tasa_ves_usd
                        precio_ves_str = f"Bs. {monto_ves:,.2f}"
                    except Exception as err:
                        logger.debug(f"Error al calcular monto VES: {err}")
                elif currency == "VES" and tasa_ves_usd > 0:
                    try:
                        monto_usd = Decimal(str(total_price)) / tasa_ves_usd
                        display_price = f"{monto_usd:,.2f} USD"
                        precio_ves_str = f"Bs. {total_price:,.2f}"
                    except Exception as err:
                        logger.debug(f"Error al calcular monto USD: {err}")

                # Procesar cada trayecto (Ida / Vuelta / Multidestino)
                trayectos_list = []
                for idx, f_obj in enumerate(itinerario):
                    if not f_obj.legs:
                        continue

                    first_l = f_obj.legs[0]
                    last_l = f_obj.legs[-1]

                    # Tipo de trayecto
                    if len(itinerario) == 2:
                        trayecto_tipo = "Ida" if idx == 0 else "Vuelta"
                    elif len(itinerario) > 2:
                        trayecto_tipo = f"Tramo {idx + 1}"
                    else:
                        trayecto_tipo = "Vuelo"

                    # Duración total calculada
                    duracion_mins = sum(getattr(leg, "duration", 0) or 0 for leg in f_obj.legs)
                    horas = duracion_mins // 60
                    mins = duracion_mins % 60
                    duracion_str = f"{horas}h {mins:02d}m" if horas > 0 else f"{mins}m"

                    # Escalas
                    num_escalas = len(f_obj.legs) - 1
                    if num_escalas == 0:
                        escalas_label = "Directo"
                        escalas_badge_class = "badge-success"
                    elif num_escalas == 1:
                        escalas_label = "1 Escala"
                        escalas_badge_class = "badge-warning"
                    else:
                        escalas_label = f"{num_escalas} Escalas"
                        escalas_badge_class = "badge-danger"

                    # Códigos IATA y Nombres
                    orig_code = (
                        first_l.departure_airport.name
                        if hasattr(first_l.departure_airport, "name")
                        else origin_code
                    )
                    dest_code = (
                        last_l.arrival_airport.name
                        if hasattr(last_l.arrival_airport, "name")
                        else destination_code
                    )

                    trayecto_info = {
                        "tipo": trayecto_tipo,
                        "origen_codigo": orig_code,
                        "origen_nombre": getattr(first_l, "departure_airport_name", "")
                        or orig_code,
                        "destino_codigo": dest_code,
                        "destino_nombre": getattr(last_l, "arrival_airport_name", "") or dest_code,
                        "salida_hora": first_l.departure_datetime.strftime("%H:%M")
                        if hasattr(first_l, "departure_datetime") and first_l.departure_datetime
                        else "--:--",
                        "salida_fecha": first_l.departure_datetime.strftime("%d %b %Y")
                        if hasattr(first_l, "departure_datetime") and first_l.departure_datetime
                        else "",
                        "llegada_hora": last_l.arrival_datetime.strftime("%H:%M")
                        if hasattr(last_l, "arrival_datetime") and last_l.arrival_datetime
                        else "--:--",
                        "llegada_fecha": last_l.arrival_datetime.strftime("%d %b %Y")
                        if hasattr(last_l, "arrival_datetime") and last_l.arrival_datetime
                        else "",
                        "duracion": duracion_str,
                        "escalas_label": escalas_label,
                        "escalas_badge_class": escalas_badge_class,
                        "aerolinea_nombre": first_l.airline.name
                        if hasattr(first_l.airline, "name")
                        else airline_name,
                        "aerolinea_codigo": first_l.airline.value
                        if hasattr(first_l.airline, "value")
                        else airline_code,
                        "vuelo_numero": first_l.flight_number or "",
                        "avion": getattr(first_l, "aircraft", "") or "",
                    }
                    trayectos_list.append(trayecto_info)

                vuelos_procesados.append(
                    {
                        "precio": display_price,
                        "precio_ves": precio_ves_str,
                        "aerolinea": airline_code,
                        "aerolinea_nombre": airline_name,
                        "trayectos": trayectos_list,
                        "real": True,
                        "is_round_trip": trip_type == TripType.ROUND_TRIP,
                        "is_multi_city": trip_type == TripType.MULTI_CITY,
                    }
                )

                if len(vuelos_procesados) >= 15:
                    break

            return vuelos_procesados

        except Exception as e:
            logger.error(f"Error crítico en FliFlightService: {e}", exc_info=True)
            return [{"error": f"Error de conexión con el proveedor de búsqueda: {str(e)}"}]

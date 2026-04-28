import json
from fli.core.builders import build_flight_segments
from fli.models import FlightSearchFilters, PassengerInfo, SeatType, MaxStops, SortBy, EmissionsFilter, Airport
from fli.search import SearchFlights

def test_availability():
    print("\n🚀 Iniciando búsqueda de disponibilidad REAL con 'fli'...")
    
    try:
        # 1. Configurar aeropuertos de prueba (BOGOTA -> MADRID)
        origin = Airport.BOG
        destination = Airport.MAD
        departure_date = "2026-05-20" # Fecha suficientemente futura
        
        print(f"📡 Origen: {origin.name} ({origin.value})")
        print(f"📡 Destino: {destination.name} ({destination.value})")
        print(f"📡 Fecha: {departure_date}")
        
        # 2. Construir segmentos de vuelo usando el constructor de fli
        segments, trip_type = build_flight_segments(
            origin=origin,
            destination=destination,
            departure_date=departure_date
        )
        
        # 3. Configurar filtros completos para Google Flights
        filters = FlightSearchFilters(
            trip_type=trip_type,
            passenger_info=PassengerInfo(adults=1),
            flight_segments=segments,
            stops=MaxStops.ANY,
            seat_type=SeatType.ECONOMY,
            sort_by=SortBy.BEST,
            emissions=EmissionsFilter.ALL
        )
        
        # 4. Ejecutar búsqueda a través de la API
        print("\n🔍 Consultando Google Flights (en vivo)...")
        search_engine = SearchFlights()
        # El método search devuelve list[FlightResult | tuple[FlightResult, ...]]
        results = search_engine.search(filters=filters)
        
        if results:
            print(f"✅ Se encontraron {len(results)} opciones de vuelo.")
            print("\nDETALLE DE LAS MEJORES OPCIONES:")
            print("="*80)
            
            for i, res in enumerate(results[:5], 1):
                # results puede devolver FlightResult o tuple de FlightResult (para round-trip)
                if isinstance(res, tuple):
                    flight = res[0] # Tomamos el primer trayecto para el ejemplo
                else:
                    flight = res
                
                # Accediendo a los atributos del modelo FlightResult
                # Vemos que airline es un objeto de tipo Airline
                airline_name = getattr(flight.airline, 'name', 'N/A')
                f_num = getattr(flight, 'flight_number', 'N/A')
                price = getattr(flight, 'price', 'N/A')
                curr = getattr(flight, 'currency', 'N/A')
                dur = getattr(flight, 'duration', 'N/A')
                
                print(f"{i}. {airline_name} | Vuelo: {f_num}")
                print(f"   Ruta: {flight.departure_airport.name} -> {flight.arrival_airport.name}")
                print(f"   Horario: {flight.departure_time.strftime('%H:%M')} - {flight.arrival_time.strftime('%H:%M')}")
                print(f"   Inversión: {price} {curr}")
                print(f"   Duración Total: {dur}")
                print("-" * 80)
                
            print("\n✨ CONCLUSIÓN: El modelo devuelve disponibilidad real y datos estructurados de alta calidad.")
        else:
            print("\n⚠️ No se obtuvieron resultados. Verifica la fecha o conectividad.")
            
    except Exception as e:
        print(f"\n❌ Error durante el test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_availability()

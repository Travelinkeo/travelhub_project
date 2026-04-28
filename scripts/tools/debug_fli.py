
import logging
import sys
import os
from datetime import datetime

# Añadir el path del proyecto para importar fli si es necesario
sys.path.append('c:/Users/ARMANDO/travelhub_project/')

from fli.search import SearchFlights
from fli.models import FlightSearchFilters, PassengerInfo, SeatType, MaxStops, SortBy, EmissionsFilter, Airport, TripType
from fli.core.builders import build_flight_segments

def test_search():
    origin = Airport.CCS
    destination = Airport.BOG
    departure_date = "2026-05-14"
    return_date = "2026-05-21"

    segments, trip_type = build_flight_segments(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date
    )

    print(f"Trip Type: {trip_type}")
    print(f"Segments Count: {len(segments)}")

    filters = FlightSearchFilters(
        trip_type=trip_type,
        passenger_info=PassengerInfo(adults=1),
        flight_segments=segments,
        stops=MaxStops.ANY,
        seat_type=SeatType.ECONOMY,
        sort_by=SortBy.BEST,
        emissions=EmissionsFilter.ALL
    )

    engine = SearchFlights()
    results = engine.search(filters=filters)

    if not results:
        print("No results found.")
        return

    print(f"Number of results: {len(results)}")
    
    # Inspeccionar el primer resultado
    res = results[0]
    print(f"First result type: {type(res)}")
    
    if isinstance(res, (tuple, list)):
        for i, item in enumerate(res):
            print(f"  Item {i} type: {type(item)}")
            if hasattr(item, 'legs'):
                print(f"  Item {i} legs: {len(item.legs)}")
                for j, leg in enumerate(item.legs):
                    print(f"    Leg {j}: {leg.departure_airport.name} -> {leg.arrival_airport.name}")
    elif hasattr(res, 'legs'):
        print(f"Result legs: {len(res.legs)}")
        for i, leg in enumerate(res.legs):
            print(f"  Leg {i}: {leg.departure_airport.name} -> {leg.arrival_airport.name}")

if __name__ == "__main__":
    test_search()

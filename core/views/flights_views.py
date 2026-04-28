import logging
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.services.amadeus_service import AmadeusService
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

class FlightSearchView(LoginRequiredMixin, View):
    template_name = "dashboard/flights/flight_search.html"
    partial_template = "dashboard/flights/partials/flight_results.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        trip_type = request.POST.get('trip_type', 'ONE_WAY')
        origin = request.POST.get('origin', '').upper()
        destination = request.POST.get('destination', '').upper()
        date = request.POST.get('date', '')
        return_date = request.POST.get('return_date', '')
        
        # Procesar Multidestino
        multi_segments = []
        if trip_type == 'MULTI_CITY':
            origins = request.POST.getlist('origin_multi[]')
            destinations = request.POST.getlist('destination_multi[]')
            dates = request.POST.getlist('date_multi[]')
            
            # Primer tramo (los campos estándar)
            multi_segments.append({'origin': origin, 'destination': destination, 'date': date})
            # Tramos adicionales
            for o, d, dt in zip(origins, destinations, dates):
                multi_segments.append({'origin': o.upper(), 'destination': d.upper(), 'date': dt})

        # Validar campos básicos
        if not origin or not destination or not date:
            return render(request, self.partial_template, {'error': 'Por favor complete todos los campos requeridos.'})

        # Extraer filtros adicionales
        stops = request.POST.get('stops', 'ANY')
        airline_filter = request.POST.get('airline_filter', '')

        # Utilizar FliFlightService para disponibilidad REAL
        from core.services.fli_service import FliFlightService
        service = FliFlightService()
        
        # Obtener resultados
        raw_results = service.buscar_vuelos(
            origin, destination, date, 
            return_date=return_date if trip_type == 'ROUND_TRIP' else None,
            multi_segments=multi_segments if trip_type == 'MULTI_CITY' else None,
            stops=stops,
            airline_filter=airline_filter
        )
        
        results = []
        error = None
        
        if isinstance(raw_results, list):
            if raw_results and 'error' in raw_results[0]:
                error = raw_results[0]['error']
            else:
                results = raw_results
        else:
             error = "No se pudieron obtener resultados."

        context = {
            'results': results,
            'error': error,
            'search_params': {
                'trip_type': trip_type,
                'origin': origin, 
                'destination': destination, 
                'date': date,
                'return_date': return_date
            }
        }
        
        return render(request, self.partial_template, context)

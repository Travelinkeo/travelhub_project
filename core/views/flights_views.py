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
        origin = request.POST.get('origin', '').upper()
        destination = request.POST.get('destination', '').upper()
        date = request.POST.get('date', '')
        
        if not origin or not destination or not date:
            return render(request, self.partial_template, {'error': 'Por favor complete todos los campos.'})

        # Fix: Convertir fecha de DD/MM/YYYY a YYYY-MM-DD si es necesario
        from datetime import datetime
        try:
             # Si viene como DD/MM/YYYY (común en datepickers hispanos)
             if '/' in date:
                 date_obj = datetime.strptime(date, '%d/%m/%Y')
                 date = date_obj.strftime('%Y-%m-%d')
             # Si ya viene como YYYY-MM-DD, se queda igual
        except ValueError:
             return render(request, self.partial_template, {'error': 'Formato de fecha inválido. Use DD/MM/YYYY.'})

        service = AmadeusService()
        
        # AmadeusService es síncrono en su método buscar_vuelos (aunque usa requests internamente)
        # Si fuese async, tendríamos que usar async_to_sync, pero el SDK es sync por defecto.
        # Sin embargo, mi implementación previa de AmadeusService es sincrona.
        
        results = service.buscar_vuelos(origin, destination, date)
        
        context = {
            'results': results if isinstance(results, list) else [],
            'error': results.get('error') if isinstance(results, dict) else None,
            'search_params': {'origin': origin, 'destination': destination, 'date': date}
        }
        
        return render(request, self.partial_template, context)

import logging

from django.core.cache import cache
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView

from apps.bookings.models import BoletoImportado, Venta
from apps.bookings.services.voucher_service import (
    generar_voucher_alojamiento,
    generar_voucher_unificado,
)

logger = logging.getLogger(__name__)


def rate_limit(limit=20, period=60):
    """
    Decorador simple de rate limiting para vistas públicas.
    """
    def decorator(view_func):
        def wrapped(self, request, *args, **kwargs):
            ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'unknown')
            key = f"rate_limit:{view_func.__name__}:{ip}"
            count = cache.get(key, 0)
            if count >= limit:
                return HttpResponse("Rate limit exceeded. Try again later.", status=429)
            cache.set(key, count + 1, period)
            return view_func(self, request, *args, **kwargs)
        return wrapped
    return decorator

class PublicItineraryView(DetailView):
    model = Venta
    queryset = Venta.all_objects.all() # Bypass TenantManager for public UUID access
    
    @method_decorator(rate_limit(limit=20, period=60))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    template_name = 'core/public/travel_portal_v2.html'
    context_object_name = 'venta'
    slug_field = 'uuid'
    slug_url_kwarg = 'token'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.object
        
        # 📈 Tracking: Registrar vista del cliente
        try:
            venta.registrar_vista_cliente()
        except Exception as e:
            logger.error(f"Error tracking client view: {e}")
        
        # Related Data
        boletos = BoletoImportado.all_objects.filter(venta_asociada=venta)
        context['boletos'] = boletos
        context['items'] = venta.items_venta.all().select_related('producto_servicio')
        context['pagos'] = venta.pagos_venta.filter(confirmado=True)
        
        # Smart Destination Detection (WOW Effect)
        first_segment = venta.segmentos_vuelo.first()
        destination_name = "Tu Próximo Viaje"
        destination_city = ""
        
        if first_segment and first_segment.destino:
            destination_name = first_segment.destino.nombre
            destination_city = first_segment.destino.nombre
        elif boletos.exists():
            # Fallback to Boleto route (e.g. CCSMAD -> Get MAD)
            first_ticket = boletos.first()
            ruta = first_ticket.ruta_vuelo or ""
            if len(ruta) >= 6:
                dest_code = ruta[-3:].strip()
                destination_name = f"Destino {dest_code}"
        
        context['destination_name'] = destination_name
        context['destination_city'] = destination_city
        
        # Hero Image Logic (AI Powered Destination Visuals)
        from apps.automation.services.ai_parser_service import AIParserService
        context['hero_image'] = AIParserService.get_destination_image(destination_city or destination_name)

        # Agency Branding
        agency = venta.agencia
        context['agency_branding'] = {
            'name': agency.nombre if agency else "TravelHub",
            'logo_url': "/static/img/logo-travelhub.svg",
            'phone': agency.telefono_principal if agency else "+1 234 567 8900",
            'email': agency.email_principal if agency else "reservas@travelhub.app",
        }
        
        return context

class PublicVoucherPDFView(DetailView):
    # Reuse logic but accessible via UUID for public download
    model = Venta
    queryset = Venta.all_objects.all() # Bypass TenantManager for public UUID access
    slug_field = 'uuid'
    
    @method_decorator(rate_limit(limit=10, period=60))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    slug_url_kwarg = 'token'

    def get(self, request, *args, **kwargs):
        venta = self.get_object()
        try:
            pdf_bytes, filename = generar_voucher_unificado(venta.pk)
            if pdf_bytes:
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                return HttpResponse("Error generando PDF", status=500)
        except Exception as e:
            logger.error(f"Error generating public PDF: {e}")
            return HttpResponse("Error interno", status=500)
class PublicHotelVoucherPDFView(View):
    @method_decorator(rate_limit(limit=10, period=60))
    def get(self, request, alojamiento_id, *args, **kwargs):
        try:
            from apps.bookings.models import AlojamientoReserva
            alojamiento = AlojamientoReserva.objects.get(pk=alojamiento_id)
            pdf_bytes, filename = generar_voucher_alojamiento(alojamiento)
            if pdf_bytes:
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                return HttpResponse("Error generando PDF", status=500)
        except Exception as e:
            logger.error(f"Error generating public hotel PDF: {e}")
            return HttpResponse("Error interno", status=500)

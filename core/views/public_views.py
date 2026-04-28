from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from apps.bookings.models import Venta, BoletoImportado
from core.services.pdf_service import generar_pdf_voucher_unificado
import logging

logger = logging.getLogger(__name__)

class PublicItineraryView(DetailView):
    model = Venta
    queryset = Venta.all_objects.all() # Bypass TenantManager for public UUID access
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
        from core.services.ai_parser_service import AIParserService
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
    slug_url_kwarg = 'token'

    def get(self, request, *args, **kwargs):
        venta = self.get_object()
        try:
            pdf_bytes, filename = generar_pdf_voucher_unificado(venta.pk)
            if pdf_bytes:
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                return HttpResponse("Error generando PDF", status=500)
        except Exception as e:
            logger.error(f"Error generating public PDF: {e}")
            return HttpResponse("Error interno", status=500)

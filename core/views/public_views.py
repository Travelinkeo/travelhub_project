from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from core.models import Venta, BoletoImportado
from core.services.pdf_service import generar_pdf_voucher_unificado
import logging

logger = logging.getLogger(__name__)

class PublicItineraryView(DetailView):
    model = Venta
    template_name = 'core/public/itinerary.html'
    context_object_name = 'venta'
    slug_field = 'uuid'
    slug_url_kwarg = 'token'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.object
        
        # Related Data
        context['boletos'] = BoletoImportado.objects.filter(venta_asociada=venta)
        context['items'] = venta.items_venta.all().select_related('producto_servicio')
        context['pagos'] = venta.pagos_venta.filter(confirmado=True)
        
        # Agency Branding
        agency = venta.agencia
        context['agency_branding'] = {
            'name': agency.nombre if agency else "TravelHub",
            # 'logo_url': agency.logo.url if agency and agency.logo else None,
            'logo_url': "/static/img/logo-travelhub.svg", # Fallback/Default
            'phone': agency.telefono_principal if agency else "+1 234 567 8900",
            'email': agency.email_principal if agency else "reservas@travelhub.app",
        }
        
        return context

class PublicVoucherPDFView(DetailView):
    # Reuse logic but accessible via UUID for public download
    model = Venta
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

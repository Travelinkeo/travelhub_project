import time
import logging
from django.views import View
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.finance.models.tax_refund import TaxRefundOpportunity

logger = logging.getLogger(__name__)

class TaxRefundDashboardView(LoginRequiredMixin, View):
    template_name = 'finance/tax_refund/dashboard.html'

    def get(self, request, *args, **kwargs):
        # 🛡️ ENGINE DE DETECCIÓN DE AGENCIA (REUTILIZADO)
        agencia = getattr(request.user, 'agencia_activa', None)
        if not agencia and hasattr(request.user, 'agencias'):
             ua = request.user.agencias.filter(activo=True).first()
             agencia = ua.agencia if ua else None
             
        # Si sigue siendo None, verificamos si es freelancer
        if not agencia and hasattr(request.user, 'perfil_freelancer'):
            agencia = request.user.perfil_freelancer.agencia

        reclamos = TaxRefundOpportunity.objects.filter(agencia=agencia).select_related(
            'boleto', 'boleto__venta_asociada', 'boleto__venta_asociada__cliente'
        ).order_by('-creado_en')
        
        context = {
            'reclamos_elegibles': reclamos.filter(estado='ELE'),
            'reclamos_tramitando': reclamos.filter(estado='TRA'),
            'reclamos_completados': reclamos.filter(estado='COM'),
        }
        return render(request, self.template_name, context)

class IniciarTramiteRefundView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para iniciar el trámite. Cambia el estado y simula la API.
    """
    def post(self, request, reclamo_id, *args, **kwargs):
        reclamo = get_object_or_404(TaxRefundOpportunity, id=reclamo_id)
        
        if reclamo.estado == 'ELE':
            # Cambiamos estado y generamos un código de tracking simulado (Ej. Global Blue API)
            reclamo.estado = 'TRA'
            reclamo.tracking_code_proveedor = f"GB-{reclamo.id.hex[:8].upper()}"
            reclamo.save()
            
            # Simulamos el delay de conexión B2B con el Partner
            time.sleep(0.8) 
        
        return render(request, 'finance/tax_refund/partials/fila_reclamo.html', {'reclamo': reclamo})

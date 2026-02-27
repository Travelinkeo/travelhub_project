from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from ..models import LiquidacionProveedor
from apps.bookings.models import BoletoImportado, AuditLog
from ..models.pasaportes import PasaporteEscaneado
# from apps.communications.models import ComunicacionProveedor
from core.mixins import SaaSMixin

class LiquidacionesListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = LiquidacionProveedor
    template_name = 'core/erp/liquidaciones.html'
    context_object_name = 'liquidaciones'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('proveedor', 'venta').order_by('-fecha_emision')
        
        # Filters
        estado = self.request.GET.get('estado')
        search = self.request.GET.get('search')

        if estado:
            queryset = queryset.filter(estado=estado)
        
        if search:
            queryset = queryset.filter(
                proveedor__nombre_comercial__icontains=search
            ) | queryset.filter(
                venta__localizador__icontains=search
            )
            
        return queryset

class PasaportesListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = PasaporteEscaneado
    template_name = 'core/erp/pasaportes.html'
    context_object_name = 'pasaportes'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente').order_by('-fecha_procesamiento')
        
        # Filters
        estado = self.request.GET.get('estado')
        search = self.request.GET.get('search')

        if estado == 'pendientes':
            queryset = queryset.filter(cliente__isnull=True)
        elif estado == 'baja_confianza':
            queryset = queryset.filter(confianza_ocr='LOW')
        
        if search:
            queryset = queryset.filter(
                Q(nombres__icontains=search) | 
                Q(apellidos__icontains=search) |
                Q(numero_pasaporte__icontains=search)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'pasaportes'
        return context

class AuditoriaListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = 'core/erp/auditoria.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('venta').order_by('-creado')
        
        # Filters
        accion = self.request.GET.get('accion')
        modelo = self.request.GET.get('modelo')
        search = self.request.GET.get('search')
        venta_id = self.request.GET.get('venta_id')

        if accion:
            queryset = queryset.filter(accion=accion)
        
        if modelo:
            queryset = queryset.filter(modelo=modelo)
            
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        
        if search:
            queryset = queryset.filter(
                Q(object_id__icontains=search) | 
                Q(descripcion__icontains=search) |
                Q(modelo__icontains=search)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'auditoria'
        
        # Statistics
        context['total_registros'] = AuditLog.objects.count()
        context['acciones_stats'] = AuditLog.objects.values('accion').annotate(total=Count('id_audit_log')).order_by('-total')
        context['modelos_stats'] = AuditLog.objects.values('modelo').annotate(total=Count('id_audit_log')).order_by('-total')[:5]
        
        return context

# class ComunicacionesListView(SaaSMixin, LoginRequiredMixin, ListView):
#     model = ComunicacionProveedor
#     template_name = 'core/erp/comunicaciones.html'
#     context_object_name = 'comunicaciones'
#     paginate_by = 20
# 
#     def get_queryset(self):
#         queryset = super().get_queryset().order_by('-fecha_recepcion')
#         
#         search = self.request.GET.get('search')
#         categoria = self.request.GET.get('categoria')
# 
#         if search:
#             queryset = queryset.filter(
#                 Q(asunto__icontains=search) | 
#                 Q(remitente__icontains=search) |
#                 Q(cuerpo_completo__icontains=search)
#             )
#             
#         if categoria:
#             queryset = queryset.filter(categoria=categoria)
#             
#         return queryset
# 
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['active_tab'] = 'comunicaciones'
#         
#         # Category Stats
#         context['categorias_stats'] = ComunicacionProveedor.objects.values('categoria').annotate(
#             total=Count('id')
#         ).order_by('-total')
#         
#         return context

class DashboardBoletosView(LoginRequiredMixin, TemplateView):
    template_name = 'core/erp/dashboard_boletos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'boletos_dashboard'
        return context

class BoletosBusquedaView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = 'core/erp/boletos_busqueda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'boletos_busqueda'
        return context

class BoletosReportesView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = 'core/erp/boletos_reportes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'boletos_reportes'
        return context

class BoletosAnulacionesView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = 'core/erp/boletos_anulaciones.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'boletos_anulaciones'
        return context

class BoletosImportarView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = 'core/erp/boletos_importar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'boletos_importar'
        
        # Fetch recent imported tickets
        qs = BoletoImportado.objects.all()
        if not self.request.user.is_superuser and hasattr(self.request.user, 'agencias'):
            ua = self.request.user.agencias.filter(activo=True).first()
            if ua:
                qs = qs.filter(agencia=ua.agencia)
        
        context['boletos'] = qs.order_by('-fecha_subida')[:20] # Show last 20
        
        # Add Active Consolidators
        from ..models import Proveedor
        proveedores = Proveedor.objects.filter(
            tipo_proveedor=Proveedor.TipoProveedorChoices.CONSOLIDADOR,
            activo=True
        ).order_by('nombre')

        # Logic to attach the current commission (Level 4 logic)
        for prov in proveedores:
            # Replicating VentaAutomationService logic: Get latest active tariff
            tarifario = prov.tarifarios.filter(activo=True).order_by('-fecha_carga').first()
            prov.comision_display = tarifario.comision_estandar if tarifario else 0

        context['proveedores'] = proveedores
        
        return context

from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from ..forms import BoletoManualForm

class BoletosManualView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = BoletoImportado
    form_class = BoletoManualForm
    template_name = 'core/erp/boletos_manual.html'
    success_url = reverse_lazy('core:boletos_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'boletos_manual'
        return context

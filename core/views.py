# Archivo: core/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.functional import cached_property

from . import ticket_parser
from .models import (
    Cliente, Venta, Factura, AsientoContable,
    PaginaCMS, PaqueteTuristicoCMS, BoletoImportado, ItemVenta,
    SegmentoVuelo, AlojamientoReserva, TrasladoServicio, ActividadServicio,
    FeeVenta, PagoVenta
)
from .serializers import (
    VentaSerializer, FacturaSerializer, AsientoContableSerializer,
    SegmentoVueloSerializer, AlojamientoReservaSerializer, TrasladoServicioSerializer,
    ActividadServicioSerializer, FeeVentaSerializer, PagoVentaSerializer
)
from .forms import BoletoManualForm, BoletoFileUploadForm, BoletoAereoUpdateForm

# --- Permisos Personalizados (Ejemplo Básico) ---
class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso personalizado para permitir solo lectura a usuarios no administradores,
    y lectura/escritura a administradores.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

# --- ViewSets para la API ERP ---

class VentaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Ventas y sus Items.
    Permite operaciones CRUD completas.
    """
    queryset = Venta.objects.select_related(
        'cliente', 'moneda', 'cotizacion_origen', 'asiento_contable_venta'
    ).prefetch_related('items_venta__producto_servicio', 'items_venta__proveedor_servicio').order_by('-fecha_venta')
    serializer_class = VentaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class FacturaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Facturas y sus Items.
    Permite operaciones CRUD completas.
    """
    queryset = Factura.objects.select_related(
        'cliente', 'moneda', 'venta_asociada', 'asiento_contable_factura'
    ).prefetch_related('items_factura').order_by('-fecha_emision')
    serializer_class = FacturaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class AsientoContableViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Asientos Contables y sus Detalles.
    Permite operaciones CRUD completas.
    """
    queryset = AsientoContable.objects.select_related(
        'moneda'
    ).prefetch_related('detalles_asiento__cuenta_contable').order_by('-fecha_contable', '-numero_asiento')
    serializer_class = AsientoContableSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def perform_create(self, serializer):
        asiento = serializer.save()

    def perform_update(self, serializer):
        asiento = self.get_object()
        if asiento.estado == AsientoContable.EstadoAsientoChoices.CONTABILIZADO and not self.request.user.is_staff:
            raise permissions.PermissionDenied(_("Los asientos contabilizados no pueden ser modificados por usuarios no administradores."))
        serializer.save()

# --- Nuevos ViewSets Phase 1 Componentes de Venta ---

class SegmentoVueloViewSet(viewsets.ModelViewSet):
    queryset = SegmentoVuelo.objects.select_related('venta', 'origen__pais', 'destino__pais').order_by('fecha_salida')
    serializer_class = SegmentoVueloSerializer
    permission_classes = [permissions.IsAuthenticated]

class AlojamientoReservaViewSet(viewsets.ModelViewSet):
    queryset = AlojamientoReserva.objects.select_related('venta', 'ciudad__pais', 'proveedor').order_by('check_in')
    serializer_class = AlojamientoReservaSerializer
    permission_classes = [permissions.IsAuthenticated]

class TrasladoServicioViewSet(viewsets.ModelViewSet):
    queryset = TrasladoServicio.objects.select_related('venta', 'proveedor').order_by('fecha_hora')
    serializer_class = TrasladoServicioSerializer
    permission_classes = [permissions.IsAuthenticated]

class ActividadServicioViewSet(viewsets.ModelViewSet):
    queryset = ActividadServicio.objects.select_related('venta', 'proveedor').order_by('fecha', 'nombre')
    serializer_class = ActividadServicioSerializer
    permission_classes = [permissions.IsAuthenticated]

class FeeVentaViewSet(viewsets.ModelViewSet):
    queryset = FeeVenta.objects.select_related('venta', 'moneda').order_by('-creado')
    serializer_class = FeeVentaSerializer
    permission_classes = [permissions.IsAuthenticated]

class PagoVentaViewSet(viewsets.ModelViewSet):
    queryset = PagoVenta.objects.select_related('venta', 'moneda').order_by('-fecha_pago')
    serializer_class = PagoVentaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def contabilizar(self, request, pk=None):
        asiento = self.get_object()
        if asiento.estado == AsientoContable.EstadoAsientoChoices.BORRADOR:
            if not asiento.esta_cuadrado():
                return Response(
                    {'error': _('El asiento no está cuadrado. Debe tener Debe == Haber.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            asiento.estado = AsientoContable.EstadoAsientoChoices.CONTABILIZADO
            asiento.save(update_fields=['estado'])
            return Response({'status': _('Asiento {} contabilizado exitosamente.').format(asiento.numero_asiento)})
        elif asiento.estado == AsientoContable.EstadoAsientoChoices.CONTABILIZADO:
            return Response({'status': _('El asiento ya está contabilizado.')}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {'error': _('Solo los asientos en borrador pueden ser contabilizados.')},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def anular(self, request, pk=None):
        asiento = self.get_object()
        if asiento.estado == AsientoContable.EstadoAsientoChoices.CONTABILIZADO:
            asiento.estado = AsientoContable.EstadoAsientoChoices.ANULADO
            asiento.save(update_fields=['estado'])
            return Response({'status': _('Asiento {} marcado como anulado. Se recomienda generar un asiento de reverso.').format(asiento.numero_asiento)})
        elif asiento.estado == AsientoContable.EstadoAsientoChoices.ANULADO:
            return Response({'status': _('El asiento ya está anulado.')}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {'error': _('Solo los asientos contabilizados pueden ser anulados de esta forma.')},
                status=status.HTTP_400_BAD_REQUEST
            )

# --- Helper reutilizable para resumen de ventas ---
from django.db.models import Sum
from .models import ProductoServicio, ItemVenta

def get_resumen_ventas_categorias():
    categoria_definiciones = [
        { 'etiqueta': 'Boletería Aérea', 'filtro': {'producto_servicio__tipo_producto': ProductoServicio.TipoProductoChoices.BOLETO_AEREO}},
        { 'etiqueta': 'Hoteles', 'filtro': {'producto_servicio__tipo_producto': ProductoServicio.TipoProductoChoices.HOTEL}},
        { 'etiqueta': 'Alquiler Vehículos', 'filtro': {'producto_servicio__tipo_producto': ProductoServicio.TipoProductoChoices.ALQUILER_AUTO}},
        { 'etiqueta': 'Traslados Terrestres', 'filtro': {'producto_servicio__tipo_producto': ProductoServicio.TipoProductoChoices.TRASLADO}},
        { 'etiqueta': 'Seguros de Viajes', 'filtro': {'producto_servicio__tipo_producto': ProductoServicio.TipoProductoChoices.SEGURO_VIAJE}},
        { 'etiqueta': 'Excursiones', 'filtro': {'producto_servicio__tipo_producto': ProductoServicio.TipoProductoChoices.TOUR_ACTIVIDAD}},
        { 'etiqueta': 'SIM / E-SIM Internacional', 'filtro': {'producto_servicio__nombre__icontains': 'SIM'}},
        { 'etiqueta': 'Servicios Adicionales', 'filtro': {'producto_servicio__tipo_producto': ProductoServicio.TipoProductoChoices.SERVICIO_ADICIONAL}},
    ]
    ventas_por_categoria = []
    total_general = 0
    for cat in categoria_definiciones:
        qs = ItemVenta.objects.filter(**cat['filtro'])
        agregado = qs.aggregate(cantidad_total=Sum('cantidad'), monto_total=Sum('total_item_venta'))
        cantidad = agregado['cantidad_total'] or 0
        monto = agregado['monto_total'] or 0
        total_general += monto
        ventas_por_categoria.append({'categoria': cat['etiqueta'], 'cantidad': cantidad, 'monto': monto})
    return ventas_por_categoria, total_general

# --- Vistas para el CMS (Django Templates) ---

class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = _("Inicio")
        return context

class PaginaCMSDetailView(DetailView):
    model = PaginaCMS
    template_name = 'core/cms/pagina_detalle.html'
    context_object_name = 'pagina'
    slug_field = 'slug'

    def get_queryset(self):
        return super().get_queryset().filter(estado=PaginaCMS.EstadoPublicacion.PUBLICADO)

class PaqueteCMSListView(ListView):
    model = PaqueteTuristicoCMS
    template_name = 'core/cms/paquete_lista.html'
    context_object_name = 'paquetes'
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().filter(estado=PaqueteTuristicoCMS.EstadoPaquete.ACTIVO).order_by('-es_destacado', 'titulo')

class BoletoImportadoListView(ListView):
    model = BoletoImportado
    template_name = 'core/dashboard_boletos.html'
    context_object_name = 'boletos'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().order_by('-fecha_subida')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upload_form'] = BoletoFileUploadForm()
        ventas_por_categoria, total_general = get_resumen_ventas_categorias()
        context['ventas_por_categoria'] = ventas_por_categoria
        context['total_general_ventas'] = total_general
        return context

@login_required
def upload_boleto_file(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = BoletoFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            boleto = form.save(commit=False)
            boleto.estado_parseo = BoletoImportado.EstadoParseo.PENDIENTE
            boleto.save()
            return redirect('core:dashboard_boletos')
    return redirect('core:dashboard_boletos')

class BoletoManualEntryView(TemplateView):
    template_name = 'core/manual_ticket_entry.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BoletoManualForm()
        context['titulo_pagina'] = _("Entrada Manual de Boleto")
        return context

    def post(self, request, *args, **kwargs):
        form = BoletoManualForm(request.POST)
        if form.is_valid():
            boleto = form.save(commit=False)
            # Para entrada manual, el nombre procesado es el mismo que el completo
            boleto.nombre_pasajero_procesado = boleto.nombre_pasajero_completo
            
            # Crear un diccionario de datos parseados para la generación de PDF
            # y para que el campo datos_parseados no esté vacío.
            # Usamos los mismos nombres de clave que ticket_parser.extract_data_from_text
            extracted_data_manual = {
                'SOURCE_SYSTEM': 'KIU', # Por defecto para entradas manuales
                'NUMERO_DE_BOLETO': boleto.numero_boleto,
                'NOMBRE_DEL_PASAJERO': boleto.nombre_pasajero_completo,
                'SOLO_NOMBRE_PASAJERO': boleto.nombre_pasajero_procesado,
                'CODIGO_IDENTIFICACION': boleto.foid_pasajero,
                'SOLO_CODIGO_RESERVA': boleto.localizador_pnr,
                'FECHA_DE_EMISION': boleto.fecha_emision_boleto.strftime('%d %b %Y').upper() if boleto.fecha_emision_boleto else 'No encontrado',
                'AGENTE_EMISOR': boleto.agente_emisor,
                'NOMBRE_AEROLINEA': boleto.aerolinea_emisora,
                'DIRECCION_AEROLINEA': boleto.direccion_aerolinea,
                'ItinerarioFinalLimpio': boleto.ruta_vuelo,
                'TARIFA': str(boleto.tarifa_base) if boleto.tarifa_base else 'No encontrado',
                'IMPUESTOS': boleto.impuestos_descripcion,
                'TOTAL': str(boleto.total_boleto) if boleto.total_boleto else 'No encontrado',
            }
            boleto.datos_parseados = extracted_data_manual
            
            # Para boletos manuales, el estado inicial es PENDIENTE para que el signal lo procese
            boleto.estado_parseo = BoletoImportado.EstadoParseo.PENDIENTE 
            boleto.save()
            
            return redirect('core:dashboard_boletos')

@login_required
def delete_boleto_importado(request: HttpRequest, pk: int) -> HttpResponse:
    boleto = get_object_or_404(BoletoImportado, pk=pk)
    if request.method == 'POST':
        boleto.delete()
        return redirect('core:dashboard_boletos')
    # If it's not a POST request, you might want to render a confirmation page
    # For now, we'll just redirect back if not POST
    return redirect('core:dashboard_boletos')

class SalesSummaryView(TemplateView):
    template_name = 'core/sales_summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ventas_por_categoria, total_general = get_resumen_ventas_categorias()
        context['ventas_por_categoria'] = ventas_por_categoria
        context['total_general_ventas'] = total_general
        context['titulo_pagina'] = _('Resumen de Ventas por Categoría')
        return context


class AirTicketsEditableListView(ListView):
    """Lista boletos aéreos (derivados de archivos importados) con edición inline de montos.

    Criterio: Se consideran 'aéreos' todos los boletos con tarifa_base no nula o ruta_vuelo presente.
    (Se puede ajustar luego usando relacion con ProductoServicio si existe.)
    """
    model = BoletoImportado
    template_name = 'core/air_tickets_editable.html'
    context_object_name = 'boletos'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().order_by('-fecha_emision_boleto', '-fecha_subida')
        # Filtro simple heurístico; TODO: agregar flag explicito si se incorpora
        return qs.filter(tarifa_base__isnull=False)

    def post(self, request, *args, **kwargs):
        boleto_id = request.POST.get('boleto_id')
        boleto = get_object_or_404(BoletoImportado, pk=boleto_id)
        form = BoletoAereoUpdateForm(request.POST, instance=boleto)
        if form.is_valid():
            form.save()
            return redirect('core:air_tickets_editable')
        # Si error, renderizar lista con errores en ese formulario específico
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context['form_errors_id'] = boleto.id_boleto_importado
        context['form_errors'] = form.errors
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        forms_map = {}
        for boleto in context['boletos']:
            forms_map[boleto.id_boleto_importado] = BoletoAereoUpdateForm(instance=boleto, prefix=str(boleto.id_boleto_importado))
        context['forms_map'] = forms_map
        context['titulo_pagina'] = _('Boletería Aérea - Edición de Montos')
        return context

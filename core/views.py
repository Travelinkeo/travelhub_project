# Archivo: core/views.py
import os
import logging
from .forms import BoletoAereoUpdateForm, BoletoFileUploadForm, BoletoManualForm

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db import models as dj_models
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, TemplateView
from rest_framework import filters, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from . import ticket_parser
from django.core.files.base import ContentFile
from .models import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    AsientoContable,
    AuditLog,  # auditoría
    CircuitoDia,
    CircuitoTuristico,
    EventoServicio,
    Factura,
    FeeVenta,
    ItemVenta,
    PaginaCMS,
    PagoVenta,
    PaqueteAereo,
    PaqueteTuristicoCMS,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    TrasladoServicio,
    Venta,
    VentaParseMetadata,
)
from .models.boletos import BoletoImportado
from .models_catalogos import Ciudad, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio
from .permissions import IsStaffOrGroupWrite

# --- Vistas para Integración con IA ---
from .serializers import (
    ActividadServicioSerializer,
    AlojamientoReservaSerializer,
    AlquilerAutoReservaSerializer,
    AsientoContableSerializer,
    AuditLogSerializer,  # auditoría
    BoletoImportadoSerializer,
    CiudadSerializer,
    CircuitoDiaSerializer,
    CircuitoTuristicoSerializer,
    EventoServicioSerializer,
    FacturaSerializer,
    FeeVentaSerializer,
    GeminiBoletoParseadoSerializer,
    MonedaSerializer,
    PagoVentaSerializer,
    PaisSerializer,
    PaqueteAereoSerializer,
    ProductoServicioSerializer,
    ProveedorSerializer,
    SegmentoVueloSerializer,
    ServicioAdicionalDetalleSerializer,
    TipoCambioSerializer,
    TrasladoServicioSerializer,
    VentaParseMetadataSerializer,
    VentaSerializer,
)

# Importar el nuevo servicio de parseo
from .services.ticket_parser_service import orquestar_parseo_de_boleto
from . import ticket_parser
from .dashboard_stats import get_dashboard_stats
from rest_framework.decorators import api_view
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class RegistrarBoletoParseadoView(APIView):
    """
    Endpoint para recibir datos de boletos parseados por un servicio de IA (Gemini).
    Valida los datos y eventualmente creará los registros correspondientes.
    """
    permission_classes = [permissions.IsAdminUser] # Proteger el endpoint

    def post(self, request, *args, **kwargs):
        serializer = GeminiBoletoParseadoSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {"status": "Datos recibidos y validados correctamente."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_ok = False
        payload = {
            'status': 'ok' if db_ok else 'degraded',
            'db': db_ok,
            'time': timezone.now().isoformat(),
            'version': os.getenv('APP_VERSION', 'dev')
        }
        return Response(payload, status=200 if db_ok else 503)

class LoginView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'detail': 'username y password requeridos'}, status=400)
        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({'detail': 'Credenciales inválidas'}, status=401)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.select_related(
        'cliente', 'moneda', 'cotizacion_origen', 'asiento_contable_venta'
    ).prefetch_related('items_venta__producto_servicio', 'items_venta__proveedor_servicio').order_by('-fecha_venta')
    serializer_class = VentaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    throttle_classes = []  # Desactivar rate limiting para esta vista
    filter_backends = [filters.SearchFilter]
    search_fields = ['localizador', 'cliente__nombres', 'cliente__apellidos', 'cliente__nombre_empresa']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            return qs.filter(dj_models.Q(creado_por=user) | dj_models.Q(creado_por__isnull=True))
        return qs

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user if self.request.user.is_authenticated else None)

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all().order_by('nombre')
    serializer_class = ProveedorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    throttle_classes = []  # Desactivar rate limiting para esta vista
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'contacto_nombre', 'contacto_email', 'iata']

class ProductoServicioViewSet(viewsets.ModelViewSet):
    queryset = ProductoServicio.objects.filter(activo=True)
    serializer_class = ProductoServicioSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_interno', 'descripcion']

class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.select_related(
        'cliente', 'moneda', 'asiento_contable_factura'
    ).prefetch_related('items_factura').order_by('-fecha_emision')
    serializer_class = FacturaSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []  # Desactivar rate limiting para esta vista
    filter_backends = [filters.SearchFilter]
    search_fields = ['numero_factura', 'cliente__nombres', 'cliente__apellidos', 'cliente__nombre_empresa']

    def list(self, request, *args, **kwargs):
        logger.info("FacturaViewSet.list() called")
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

class AsientoContableViewSet(viewsets.ModelViewSet):
    queryset = AsientoContable.objects.select_related(
        'moneda'
    ).prefetch_related('detalles_asiento__cuenta_contable').order_by('-fecha_contable', '-numero_asiento')
    serializer_class = AsientoContableSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        asiento = self.get_object()
        if asiento.estado == AsientoContable.EstadoAsientoChoices.CONTABILIZADO and not self.request.user.is_staff:
            raise permissions.PermissionDenied(_("Los asientos contabilizados no pueden ser modificados por usuarios no administradores."))
        serializer.save()

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

class AlquilerAutoReservaViewSet(viewsets.ModelViewSet):
    queryset = AlquilerAutoReserva.objects.all().select_related('venta', 'proveedor', 'ciudad_retiro', 'ciudad_devolucion')
    serializer_class = AlquilerAutoReservaSerializer
    filterset_fields = ['venta', 'proveedor', 'ciudad_retiro', 'ciudad_devolucion']
    search_fields = ['numero_confirmacion', 'compania_rentadora']
    permission_classes = [IsStaffOrGroupWrite]

class EventoServicioViewSet(viewsets.ModelViewSet):
    queryset = EventoServicio.objects.all().select_related('venta', 'proveedor')
    serializer_class = EventoServicioSerializer
    filterset_fields = ['venta', 'proveedor']
    search_fields = ['nombre_evento', 'codigo_boleto_evento']
    permission_classes = [IsStaffOrGroupWrite]

class CircuitoTuristicoViewSet(viewsets.ModelViewSet):
    queryset = CircuitoTuristico.objects.all().select_related('venta').prefetch_related('dias')
    serializer_class = CircuitoTuristicoSerializer
    filterset_fields = ['venta']
    search_fields = ['nombre_circuito']
    permission_classes = [IsStaffOrGroupWrite]

class CircuitoDiaViewSet(viewsets.ModelViewSet):
    queryset = CircuitoDia.objects.all().select_related('circuito', 'circuito__venta')
    serializer_class = CircuitoDiaSerializer
    filterset_fields = ['circuito', 'circuito__venta']
    search_fields = ['titulo']
    permission_classes = [IsStaffOrGroupWrite]

class PaqueteAereoViewSet(viewsets.ModelViewSet):
    queryset = PaqueteAereo.objects.all().select_related('venta')
    serializer_class = PaqueteAereoSerializer
    filterset_fields = ['venta']
    search_fields = ['nombre_paquete']
    permission_classes = [IsStaffOrGroupWrite]

class ServicioAdicionalDetalleViewSet(viewsets.ModelViewSet):
    queryset = ServicioAdicionalDetalle.objects.all().select_related('venta', 'proveedor')
    serializer_class = ServicioAdicionalDetalleSerializer
    filterset_fields = ['venta', 'proveedor', 'tipo_servicio']
    search_fields = ['codigo_referencia']
    permission_classes = [IsStaffOrGroupWrite]

class FeeVentaViewSet(viewsets.ModelViewSet):
    queryset = FeeVenta.objects.select_related('venta', 'moneda').order_by('-creado')
    serializer_class = FeeVentaSerializer
    permission_classes = [permissions.IsAuthenticated]

class PagoVentaViewSet(viewsets.ModelViewSet):
    queryset = PagoVenta.objects.select_related('venta', 'moneda').order_by('-fecha_pago')
    serializer_class = PagoVentaSerializer
    permission_classes = [permissions.IsAuthenticated]

class VentaParseMetadataViewSet(viewsets.ModelViewSet):
    queryset = VentaParseMetadata.objects.select_related('venta').order_by('-creado')
    serializer_class = VentaParseMetadataSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def contabilizar(self, request, pk=None):
        obj = self.get_object()
        from .models import AsientoContable, VentaParseMetadata
        if isinstance(obj, VentaParseMetadata):
            asiento = getattr(obj.venta, 'asiento_contable_venta', None)
            if asiento is None:
                return Response({'error': _('La venta no tiene asiento contable asociado.')}, status=status.HTTP_400_BAD_REQUEST)
        else:
            asiento = obj
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
        obj = self.get_object()
        from .models import AsientoContable, VentaParseMetadata
        if isinstance(obj, VentaParseMetadata):
            asiento = getattr(obj.venta, 'asiento_contable_venta', None)
            if asiento is None:
                return Response({'error': _('La venta no tiene asiento contable asociado.')}, status=status.HTTP_400_BAD_REQUEST)
        else:
            asiento = obj
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

class BoletoImportadoViewSet(viewsets.ModelViewSet):
    queryset = BoletoImportado.objects.all()
    serializer_class = BoletoImportadoSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [filters.SearchFilter]
    search_fields = ['numero_boleto', 'nombre_pasajero_procesado', 'localizador_pnr', 'aerolinea_emisora']

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

class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = _("Inicio")
        context['dashboard_stats'] = get_dashboard_stats()
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
            boleto.nombre_pasajero_procesado = boleto.nombre_pasajero_completo
            
            extracted_data_manual = {
                'SOURCE_SYSTEM': 'KIU',
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
            
            boleto.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO 
            boleto.save()

            messages.warning(request, "Intentando generar PDF...")
            try:
                pdf_bytes, pdf_filename = ticket_parser.generate_ticket(boleto.datos_parseados)
                boleto.archivo_pdf_generado.save(pdf_filename, ContentFile(pdf_bytes), save=True)
                messages.success(request, f"PDF '{pdf_filename}' generado y guardado exitosamente.")
            except Exception as e:
                messages.error(request, f"El boleto fue guardado, pero no se pudo generar el PDF: {e}")
            
            return redirect('core:dashboard_boletos')

@login_required
def delete_boleto_importado(request: HttpRequest, pk: int) -> HttpResponse:
    boleto = get_object_or_404(BoletoImportado, pk=pk)
    if request.method == 'POST':
        boleto.delete()
        return redirect('core:dashboard_boletos')
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
    model = BoletoImportado
    template_name = 'core/air_tickets_editable.html'
    context_object_name = 'boletos'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().order_by('-fecha_emision_boleto', '-fecha_subida')
        return qs.filter(tarifa_base__isnull=False)

    def post(self, request, *args, **kwargs):
        boleto_id = request.POST.get('boleto_id')
        boleto = get_object_or_404(BoletoImportado, pk=boleto_id)
        form = BoletoAereoUpdateForm(request.POST, instance=boleto)
        if form.is_valid():
            form.save()
            return redirect('core:air_tickets_editable')
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

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('venta').order_by('-creado')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['modelo','accion','venta']
    search_fields = ['object_id','descripcion']
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        created_from = self.request.query_params.get('created_from')
        created_to = self.request.query_params.get('created_to')
        if created_from:
            qs = qs.filter(creado__date__gte=created_from)
        if created_to:
            qs = qs.filter(creado__date__lte=created_to)
        return qs

class PaisViewSet(viewsets.ModelViewSet):
    queryset = Pais.objects.all()
    serializer_class = PaisSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    throttle_classes = []  # Desactivar rate limiting para esta vista
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_iso_2', 'codigo_iso_3']

class CiudadViewSet(viewsets.ModelViewSet):
    queryset = Ciudad.objects.select_related('pais').all()
    serializer_class = CiudadSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    throttle_classes = []  # Desactivar rate limiting para esta vista
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'pais__nombre', 'region_estado']
    ordering_fields = ['nombre', 'pais__nombre']
    ordering = ['nombre']  # Orden por defecto

class MonedaViewSet(viewsets.ModelViewSet):
    queryset = Moneda.objects.all()
    serializer_class = MonedaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None  # Cargar todas las monedas a la vez
    throttle_classes = []  # Desactivar rate limiting para esta vista
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_iso']

class TipoCambioViewSet(viewsets.ModelViewSet):
    queryset = TipoCambio.objects.select_related('moneda_origen', 'moneda_destino').all()
    serializer_class = TipoCambioSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class BoletoUploadAPIView(APIView):
    """
    Endpoint para subir un archivo de boleto (PDF/TXT), parsearlo
    de forma inteligente (IA con fallback a Regex) y guardar los
    resultados en la base de datos.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info("-> BoletoUploadAPIView.post() ha sido alcanzado.")
        
        archivo_subido = request.FILES.get('boleto_file')
        if not archivo_subido:
            logger.warning("Intento de subida sin archivo.")
            return Response(
                {"error": "No se proporcionó ningún archivo en el campo 'boleto_file'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Orquestar el parseo del boleto usando el servicio
        datos_parseados, mensaje = orquestar_parseo_de_boleto(archivo_subido)
        
        if not datos_parseados:
            logger.error(f"Fallo en el parseo del archivo '{archivo_subido.name}': {mensaje}")
            return Response(
                {"error": mensaje},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Guardar el boleto original y los datos parseados en el modelo
        try:
            boleto_importado = BoletoImportado.objects.create(
                archivo_boleto=archivo_subido, # CORREGIDO: Nombre del campo
                datos_parseados=datos_parseados,
            )
            
        except Exception as e:
            logger.exception(f"Error al guardar el boleto '{archivo_subido.name}' en la base de datos.")
            return Response(
                {"error": f"Error al guardar en la base de datos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # 3. (Opcional) Generar el PDF final y guardarlo en el modelo
        try:
            # Usar el generador de PDF unificado
            pdf_bytes, nombre_archivo_generado = ticket_parser.generate_ticket(datos_parseados)
            
            if pdf_bytes:
                boleto_importado.archivo_pdf_generado.save(nombre_archivo_generado, ContentFile(pdf_bytes), save=True)
        except Exception as e:
            logger.warning(f"No se pudo generar el PDF para el boleto {boleto_importado.id_boleto_importado}, pero el parseo fue exitoso. Error: {str(e)}")


        logger.info(f"-> Boleto {boleto_importado.id_boleto_importado} procesado y guardado exitosamente.")

        # 4. Devolver una respuesta exitosa con los datos extraídos
        return Response(
            {
                "mensaje": "Boleto procesado y guardado con éxito.",
                "id_boleto_importado": boleto_importado.id_boleto_importado,
                "datos_extraidos": datos_parseados
            },
            status=status.HTTP_201_CREATED
        )

def test_api_view(request):
    print("!!!!!! TEST API VIEW WAS CALLED !!!!!!")
    return JsonResponse({"status": "ok", "message": "Hello from the test API!"})

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def dashboard_stats_api(request):
    """API endpoint para estadísticas del dashboard"""
    stats = get_dashboard_stats()
    return Response(stats)

@api_view(['POST'])
def ai_agent_chat(request):
    """API endpoint para chat con el agente IA"""
    from .ai_agent import agent
    import asyncio
    
    try:
        message = request.data.get('message', '')
        if not message:
            return Response({'error': 'Mensaje requerido'}, status=400)
        
        # Ejecutar consulta asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(agent.process_query(message))
        loop.close()
        
        return Response({
            'response': response,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)
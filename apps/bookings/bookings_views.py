import json
import logging
import os
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.common.mixins.export_mixin import ExportMixin
from apps.crm.models import OportunidadViaje
from core.api import AuditLog, HtmxResponseMixin, SaaSMixin, get_agencia_from_request

from .models import FeeVenta, ItemVenta, PagoVenta, Venta, VentaAuditFinding

logger = logging.getLogger(__name__)


class BookingBaseMixin(SaaSMixin, LoginRequiredMixin):
    """BookingBaseMixin."""

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "ventas"
        return context


# --- VENTAS ---


class VentaListView(ExportMixin, HtmxResponseMixin, BookingBaseMixin, ListView):
    """VentaListView."""

    model = Venta
    template_name = "bookings/venta_list.html"
    htmx_template_name = "bookings/partials/venta_list_rows.html"
    context_object_name = "ventas"
    paginate_by = 25
    export_fields = [
        "localizador",
        "cliente__nombres",
        "cliente__apellidos",
        "fecha_venta",
        "moneda__codigo_iso",
        "total_venta",
        "monto_pagado",
        "saldo_pendiente",
        "estado",
    ]
    export_filename = "ventas"

    def get_queryset(self):
        """get_queryset."""
        queryset = (
            super().get_queryset().select_related("cliente", "moneda").order_by("-fecha_venta")
        )
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(localizador__icontains=q)
                | Q(cliente__nombres__icontains=q)
                | Q(cliente__apellidos__icontains=q)
            )
        return queryset


class VentaDetailView(BookingBaseMixin, DetailView):
    """VentaDetailView."""

    model = Venta
    template_name = "bookings/venta_detail_modern.html"
    context_object_name = "venta"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items_venta.all().select_related(
            "producto_servicio", "proveedor_servicio"
        )
        context["fees"] = self.object.fees_venta.all().select_related("moneda")
        context["pagos"] = self.object.pagos_venta.all().select_related("moneda")
        return context


class VentaTimelineView(BookingBaseMixin, DetailView):
    """VentaTimelineView."""

    model = Venta
    template_name = "bookings/venta_timeline.html"
    context_object_name = "venta"

    def get_queryset(self):
        """get_queryset."""
        return (
            super()
            .get_queryset()
            .select_related("cliente", "moneda")
            .prefetch_related("metadata_parseo", "boletos_adjuntos", "pagos_venta")
        )

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        venta = self.object

        # Recopilar eventos curados
        events = []

        # 1. Lead Creado (si hay oportunidad asociada)
        # Buscamos oportunidades del mismo cliente creadas antes o cerca de la venta
        oportunidad = (
            OportunidadViaje.objects.filter(cliente=venta.cliente).order_by("-creado_en").first()
        )
        if oportunidad:
            events.append(
                {
                    "type": "lead",
                    "title": "Lead Captado",
                    "description": f"El cliente inició contacto via {oportunidad.origen or 'Canal Digital'} y fue asignado al Kanban.",
                    "date": oportunidad.creado_en,
                    "icon": "person_add",
                    "color": "slate",
                }
            )

        # 2. Documentos Subidos (BoletoImportado)
        boletos = venta.boletos_adjuntos.all()
        for b in boletos:
            events.append(
                {
                    "type": "upload",
                    "title": "Boleto Subido al Sistema",
                    "description": f"Se subió el archivo {os.path.basename(b.archivo_boleto.name) if b.archivo_boleto else 'Sin nombre'}. Formato: {b.get_formato_detectado_display()}.",
                    "date": b.fecha_subida,
                    "icon": "document_scanner",
                    "color": "slate",
                }
            )

        # 3. Magia IA (Metadata de Parseo)
        for meta in venta.metadata_parseo.all():
            events.append(
                {
                    "type": "ia",
                    "title": "Venta construida por Gemini AI",
                    "description": f"La IA extrajo datos de {meta.fuente}. Consistencia de montos: {meta.amount_consistency or 'Alta'}.",
                    "date": meta.creado,
                    "icon": "auto_awesome",
                    "color": "emerald",
                    "is_ia": True,
                }
            )

        # 4. Pagos
        for p in venta.pagos_venta.all().select_related("moneda"):
            events.append(
                {
                    "type": "payment",
                    "title": f"Pago Registrado ({p.get_metodo_display()})"
                    if p.confirmado
                    else "Esperando Conciliación de Pago",
                    "description": f"Referencia: {p.referencia or 'S/R'}. Monto: {p.monto} {p.moneda.codigo_iso}.",
                    "date": p.fecha_pago,
                    "icon": "payments" if p.confirmado else "schedule",
                    "color": "emerald" if p.confirmado else "amber",
                    "monto": p.monto,
                    "moneda": p.moneda.simbolo,
                }
            )

        # 5. AuditLogs (Cualquier cambio manual)
        logs = AuditLog.objects.filter(venta=venta).select_related("user").exclude(accion="CREATE")
        for log in logs:
            events.append(
                {
                    "type": "audit",
                    "title": log.descripcion or f"Cambio en {log.modelo}",
                    "description": f"Acción {log.get_accion_display()} realizada por {log.user.username if log.user else 'Sistema'}.",
                    "date": log.creado,
                    "icon": "history",
                    "color": "slate",
                }
            )

        # Ordenar por fecha descendente (más reciente arriba)
        # Usamos una fecha muy antigua como fallback si el campo date es None
        epoch = timezone.make_aware(datetime(1970, 1, 1))
        events.sort(key=lambda x: x["date"] if x["date"] else epoch, reverse=True)

        context["timeline_events"] = events
        return context


class VentaCreateView(BookingBaseMixin, CreateView):
    """VentaCreateView."""

    model = Venta
    template_name = "bookings/venta_form.html"
    fields = ["cliente", "moneda", "tipo_venta", "descripcion_general", "notas"]
    success_url = reverse_lazy("bookings:venta_list")

    def form_valid(self, form):
        """form_valid."""
        messages.success(self.request, "Venta creada correctamente.")
        return super().form_valid(form)


class VentaUpdateView(BookingBaseMixin, UpdateView):
    """VentaUpdateView."""

    model = Venta
    template_name = "bookings/venta_form.html"
    fields = ["cliente", "moneda", "estado", "tipo_venta", "descripcion_general", "notas"]

    def get_success_url(self):
        """get_success_url."""
        return reverse_lazy("bookings:venta_detail", kwargs={"pk": self.object.pk})


class VentaDeleteView(BookingBaseMixin, DeleteView):
    """VentaDeleteView."""

    model = Venta
    template_name = "bookings/venta_confirm_delete.html"
    success_url = reverse_lazy("bookings:venta_list")

    def form_valid(self, form):
        """form_valid."""
        success_url = self.get_success_url()
        obj = self.get_object()

        # 1. Soft-delete de componentes dependientes que heredan de SoftDeleteModel
        obj.items_venta.all().update(is_deleted=True, deleted_at=timezone.now())
        obj.segmentos_vuelo.all().update(is_deleted=True, deleted_at=timezone.now())
        obj.alojamientos.all().update(is_deleted=True, deleted_at=timezone.now())
        obj.traslados.all().update(is_deleted=True, deleted_at=timezone.now())
        obj.actividades.all().update(is_deleted=True, deleted_at=timezone.now())
        obj.fees_venta.all().update(is_deleted=True, deleted_at=timezone.now())
        if hasattr(obj, "alquileres_autos"):
            obj.alquileres_autos.all().update(is_deleted=True, deleted_at=timezone.now())
        if hasattr(obj, "eventos_servicios"):
            obj.eventos_servicios.all().update(is_deleted=True, deleted_at=timezone.now())

        # Soft-delete de modelos financieros dependientes
        if hasattr(obj, "comisiones_agente"):
            obj.comisiones_agente.all().update(is_deleted=True, deleted_at=timezone.now())
        if hasattr(obj, "pagos_finanzas_recaudacion"):
            obj.pagos_finanzas_recaudacion.all().update(is_deleted=True, deleted_at=timezone.now())
        if hasattr(obj, "transacciones_pago"):
            obj.transacciones_pago.all().update(is_deleted=True, deleted_at=timezone.now())

        # 2. Eliminación física de dependencias secundarias que no soportan Soft Delete
        obj.pagos_venta.all().delete()
        if hasattr(obj, "circuitos_turisticos"):
            obj.circuitos_turisticos.all().delete()
        if hasattr(obj, "paquetes_aereos"):
            obj.paquetes_aereos.all().delete()
        if hasattr(obj, "cruceros"):
            obj.cruceros.all().delete()
        if hasattr(obj, "servicios_adicionales"):
            obj.servicios_adicionales.all().delete()

        # 3. Hard-delete de la Venta (físico, ya que las dependencias ya se procesaron)
        obj.hard_delete()

        messages.success(
            self.request, f"Venta {obj.localizador or obj.id_venta} eliminada correctamente."
        )
        return redirect(success_url)


# --- ⚡ CONTROLADORES HÍBRIDOS (HTMX) ---
# ¿Por qué "Híbridos"?: Tienen un Patrón de Dualidad Defensiva. Si el JS/Frontend del navegador falla o expira,
# devuelven un fallback al flujo clásico de Django con `redirect()` Full Page.
# Si el front-end está sano y envía `HX-Request`, hacen un bypass del flujo normal y escupen
# un componente atómico de HTML (Hot-Swap) ultrarrápido para inyectarse directo en la vista sin recargar.


class ItemVentaCreateView(BookingBaseMixin, CreateView):
    """
    🚨 CRÍTICO | ⚡ HTMX
    Punto de inyección rápida de filas de facturación.

    ¿Por qué?: El usuario emitiendo boletos no puede tolerar Full Page Reloads (demasiada latencia y parpadeos).
    Esto guarda el Item, detona el recálculo y renderiza únicamente la "Calculadora de Totales Contables",
    para que Alpine.js/HTMX reemplace instantáneamente el componente en el Canvas visual.
    """

    model = ItemVenta
    template_name = "bookings/partials/item_venta_form.html"
    fields = [
        "producto_servicio",
        "descripcion_personalizada",
        "cantidad",
        "precio_unitario_venta",
        "costo_neto_proveedor",
        "proveedor_servicio",
    ]

    def form_valid(self, form):
        """
        # 🚨 TRIGGER FINANCIERO EN TIEMPO REAL:
        # Al guardar la fila, accionamos de inmediato al motor Aritmético de DB para consolidar la deuda ascendente.
        """
        venta = get_object_or_404(Venta, pk=self.kwargs["venta_pk"])
        form.instance.venta = venta
        form.save()
        from apps.bookings.services.venta_service import VentaService

        VentaService.recalculate_finances(venta.pk)

        if self.request.headers.get("HX-Request"):
            return render(
                self.request, "bookings/partials/venta_totals_card.html", {"venta": venta}
            )
        return redirect("bookings:venta_detail", pk=venta.pk)


class FeeVentaCreateView(BookingBaseMixin, CreateView):
    """
    🚨 CRÍTICO | ⚡ HTMX
    Agrega sobrecargos por Mark-Ups o comisiones de emisión ocultas.
    Se aprovecha del piggy-back render logic para repintar el saldo de totalización en Front-End al vuelo.
    """

    model = FeeVenta
    template_name = "bookings/partials/feeventa_form.html"
    fields = ["tipo_fee", "monto", "descripcion"]

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        context["venta_pk"] = self.kwargs["venta_pk"]
        return context

    def form_valid(self, form):
        """form_valid."""
        venta = get_object_or_404(Venta, pk=self.kwargs["venta_pk"])
        form.instance.venta = venta
        form.instance.moneda = venta.moneda
        from core.api import get_user_active_agency

        agencia = get_user_active_agency(self.request.user)
        if agencia:
            form.instance.agencia = agencia
        form.save()
        from apps.bookings.services.venta_service import VentaService

        VentaService.recalculate_finances(venta.pk)

        if self.request.headers.get("HX-Request"):
            from django.http import HttpResponse

            response = HttpResponse()
            response["HX-Refresh"] = "true"
            return response
        return redirect("bookings:venta_detail", pk=venta.pk)


class PagoVentaCreateView(BookingBaseMixin, CreateView):
    """
    🚨 CRÍTICO | ⚡ HTMX
    Delegación asíncrona de reportes manuales de pago de saldos offline (Zelle, Swift, Cheques).

    ¿Por qué?: Evitamos colisiones de caja mutante. Si el agente "A" carga una tarjeta y el agente "B" un efectivo
    a la misma reserva simultáneamente, HTMX forza un refresh del DOM de saldos post-inyección transaccional,
    devolviendo a cada agente la verdad única que resulta de `recalcular_finanzas`.
    """

    model = PagoVenta
    template_name = "bookings/partials/pagoventa_form.html"
    fields = ["monto", "metodo", "referencia"]

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        context["venta_pk"] = self.kwargs["venta_pk"]
        return context

    def form_valid(self, form):
        """form_valid."""
        venta = get_object_or_404(Venta, pk=self.kwargs["venta_pk"])
        form.instance.venta = venta
        form.instance.moneda = venta.moneda
        from core.api import get_user_active_agency

        agencia = get_user_active_agency(self.request.user)
        if agencia:
            form.instance.agencia = agencia
        form.save()
        from apps.bookings.services.venta_service import VentaService

        VentaService.recalculate_finances(venta.pk)

        if self.request.headers.get("HX-Request"):
            from django.http import HttpResponse

            response = HttpResponse()
            response["HX-Refresh"] = "true"
            return response
        return redirect("bookings:venta_detail", pk=venta.pk)


class ItemVentaUpdateView(BookingBaseMixin, UpdateView):
    """ItemVentaUpdateView."""

    model = ItemVenta
    template_name = "bookings/partials/item_venta_form.html"
    fields = [
        "descripcion_personalizada",
        "cantidad",
        "precio_unitario_venta",
        "costo_neto_proveedor",
    ]

    def form_valid(self, form):
        """form_valid."""
        response = super().form_valid(form)
        from apps.bookings.services.venta_service import VentaService

        VentaService.recalculate_finances(self.object.venta.pk)
        return response

    def get_success_url(self):
        """get_success_url."""
        return reverse_lazy("bookings:venta_detail", kwargs={"pk": self.object.venta.pk})


# --- 🧠 INTELIGENCIA FINANCIERA ---


class RevenueLeakDashboardView(BookingBaseMixin, ListView):
    """
    Dashboard de Auditoría AI para la detección de fugas de ingresos.
    """

    model = VentaAuditFinding
    template_name = "bookings/audit_dashboard.html"
    context_object_name = "findings"

    def get_queryset(self):
        """get_queryset."""
        # Obtener la agencia activa del usuario logueado de forma segura
        try:
            agencia = get_agencia_from_request(self.request)
        except Exception:
            agencia = None

        return (
            VentaAuditFinding.all_objects.filter(agencia=agencia)
            .select_related("venta", "venta__cliente")
            .order_by("-fecha_deteccion")
        )

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        findings = self.get_queryset()

        # Filtro rápido para stats
        context["stats"] = {
            "total_findings": findings.count(),
            "critical_leaks": findings.filter(tipo__in=["CZS", "MSC"]).count(),
            "money_at_risk": findings.aggregate(total=Sum("venta__total_venta"))["total"] or 0,
            "pending_review": findings.count(),  # Por ahora todos son pendientes
        }

        context["active_tab"] = "auditoria"
        return context


def resolve_finding_htmx(request, pk):
    """
    Endpoint rápido para resolver o ignorar hallazgos vía HTMX.
    """
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    from core.api import get_user_active_agency

    agencia = get_user_active_agency(request.user)

    finding = get_object_or_404(VentaAuditFinding.all_objects, pk=pk, agencia=agencia)
    action = request.POST.get("action")

    if action == "resolve":
        finding.estado = VentaAuditFinding.FindingStatus.SOLUCIONADO
        finding.es_hallazgo_valido = True
    elif action == "ignore":
        finding.estado = VentaAuditFinding.FindingStatus.IGNORADO
        finding.es_hallazgo_valido = False

    finding.fecha_resolucion = timezone.now()
    finding.resuelto_por = request.user
    finding.save()

    # Devolver el nuevo Badge de estado
    color = "emerald" if action == "resolve" else "slate"
    icon = "check_circle" if action == "resolve" else "block"

    return HttpResponse(f"""
        <span class="px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-widest bg-{color}-500/10 text-{color}-500 border border-{color}-500/20 flex items-center gap-1 animate-pulse">
            <span class="material-symbols-outlined !text-[12px]">{icon}</span>
            {finding.get_estado_display()}
        </span>
    """)


@login_required
def dashboard_main(request):
    """Carga el esqueleto HTML del panel de control."""
    return render(request, "dashboard/main.html")


@login_required
def dashboard_stats_htmx(request):
    """Calcula las métricas y devuelve el fragmento HTML reactivo."""
    try:
        dias = int(request.GET.get("dias", 7))
    except (ValueError, TypeError):
        dias = 7

    fecha_inicio = timezone.now() - timedelta(days=dias)

    # Querysets Base (Usamos el manager por defecto que filtra por agencia del usuario)
    ventas_periodo = Venta.objects.filter(fecha_venta__gte=fecha_inicio)

    # KPIs Consolidados
    totales_ventas = ventas_periodo.aggregate(
        ingresos_brutos=Coalesce(Sum("total_venta"), Value(0), output_field=DecimalField()),
        liquidez_real=Coalesce(Sum("monto_pagado"), Value(0), output_field=DecimalField()),
    )

    # Costos y Ganancias (Asumiendo que ItemVenta hereda el filtro de Venta)
    totales_costos = ItemVenta.objects.filter(venta__in=ventas_periodo).aggregate(
        deuda_proveedores=Coalesce(
            Sum("costo_neto_proveedor"), Value(0), output_field=DecimalField()
        ),
        ganancia_neta=Coalesce(
            Sum(F("comision_agencia_monto") + F("fee_agencia_interno")),
            Value(0),
            output_field=DecimalField(),
        ),
    )

    # Datos para la Gráfica
    ventas_por_dia = (
        ventas_periodo.annotate(dia=TruncDate("fecha_venta"))
        .values("dia")
        .annotate(total_dia=Coalesce(Sum("total_venta"), Value(0), output_field=DecimalField()))
        .order_by("dia")
    )

    fechas_chart = [v["dia"].strftime("%d %b") for v in ventas_por_dia]
    totales_chart = [float(v["total_dia"]) for v in ventas_por_dia]

    context = {
        "ingresos_brutos": totales_ventas["ingresos_brutos"],
        "liquidez_real": totales_ventas["liquidez_real"],
        "deuda_proveedores": totales_costos["deuda_proveedores"],
        "ganancia_neta": totales_costos["ganancia_neta"],
        "fechas_chart": json.dumps(fechas_chart),
        "totales_chart": json.dumps(totales_chart),
    }

    return render(request, "dashboard/partials/stats.html", context)


@login_required
def whatsapp_qr_view(request):
    """
    Vista principal de estado de WhatsApp (Migrada a Evolution API v2).
    """
    from apps.communications.services.whatsapp_unified import WhatsAppService

    agencia = getattr(request, "agencia", None)
    if not agencia:
        from core.api import get_agencia_from_request

        try:
            agencia = get_agencia_from_request(request)
        except Exception:
            return HttpResponse("No se detectó contexto de agencia.", status=403)
    if not agencia:
        return HttpResponse("No se detectó contexto de agencia.", status=403)

    # Usamos el slug de la agencia para multi-instancia
    session_name = agencia.subdominio_slug

    # Manejo de acciones (Logout)
    action = request.GET.get("action")
    if action == "logout" or request.method == "POST" and request.GET.get("action") == "logout":
        WhatsAppService.logout(session_name)
        # Forzar estado desconectado tras logout
        estado_raw = "DISCONNECTED"
    else:
        estado_raw = WhatsAppService.get_status(session_name)

    # Evolution: WORKING, DISCONNECTED, CONNECTING
    estado_ui = "disconnected"
    logger.debug(f"whatsapp_qr_view -> session_name: {session_name}, estado_raw: {estado_raw}")
    if estado_raw == "WORKING":
        estado_ui = "connected"
    elif estado_raw == "CONNECTING":
        estado_ui = "connecting"
    else:
        estado_ui = "disconnected"
    logger.debug(f"whatsapp_qr_view -> final estado_ui: {estado_ui}")

    qr_code = None
    if estado_ui != "connected":
        qr_code = WhatsAppService.get_qr_code(session_name)
        if not qr_code:
            # Intentar despertar la instancia si no hay QR
            WhatsAppService.start_session(session_name)
            qr_code = WhatsAppService.get_qr_code(session_name)

        # Si tenemos un QR, el estado debe ser 'connecting' (esperando escaneo)
        if qr_code:
            estado_ui = "connecting"

    context = {
        "estado": estado_ui,
        "instancia": session_name,
        "qr_code": qr_code,
    }
    # Intentar cargar whatsapp_qr_new.html, si no existe, usar whatsapp_qr.html
    try:
        return render(request, "dashboard/partials/whatsapp_qr_new.html", context)
    except Exception:
        return render(request, "dashboard/partials/whatsapp_qr.html", context)


@login_required
def whatsapp_pairing_code_view(request):
    """whatsapp_pairing_code_view."""
    logger.info("whatsapp_pairing_code_view hit!")
    """
    Vista HTMX que solicita el código de emparejamiento por número de teléfono.
    El usuario ingresa su número y recibe un código de 8 caracteres para ingresar en WhatsApp.
    """
    agencia = getattr(request, "agencia", None)
    if not agencia:
        from core.api import get_agencia_from_request

        try:
            agencia = get_agencia_from_request(request)
        except Exception:
            return HttpResponse("No se detectó contexto de agencia.", status=403)
    if not agencia:
        return HttpResponse("No se detectó contexto de agencia.", status=403)

    instancia_name = agencia.subdominio_slug
    if request.method == "POST":
        numero = request.POST.get("numero_telefono", "").strip()
        if not numero:
            return render(
                request,
                "dashboard/partials/whatsapp_pairing_result.html",
                {
                    "error": "Debes ingresar un número de teléfono.",
                    "instancia": instancia_name,
                },
            )

        # En Evolution API v2, usamos el servicio directamente para Pairing Code
        from apps.communications.services.evolution_api_service import EvolutionService

        resultado = EvolutionService.get_pairing_code(instancia_name, numero)

        if resultado.get("success"):
            return render(
                request,
                "dashboard/partials/whatsapp_pairing_result.html",
                {
                    "codigo": resultado["code"],
                    "numero": numero,
                    "instancia": instancia_name,
                },
            )
        else:
            return render(
                request,
                "dashboard/partials/whatsapp_pairing_result.html",
                {
                    "error": resultado.get("error", "Error desconocido al obtener el código."),
                    "instancia": instancia_name,
                },
            )

    return HttpResponse("Método no permitido", status=405)

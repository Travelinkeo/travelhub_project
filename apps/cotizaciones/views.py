import json
import logging
import re
import time

import requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.automation.services.ai_engine import ai_engine
from core.api import SaaSMixin
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin
from core.forms import CotizacionForm, ItemCotizacionFormSet

from .ai_schemas import CotizacionMagicSchema
from .models import Cotizacion, ItemCotizacion
from .pdf_service import generar_pdf_cotizacion
from .serializers import CotizacionSerializer, ItemCotizacionSerializer

try:
    from apps.finance.models import TasaCambioBCV
except ImportError:
    TasaCambioBCV = None


# Regex para identificar aerolíneas en texto crudo de GDS
re_airlines = re.compile(
    r"\b([A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])\s*(?:\d{2,4})[A-Z]?(?:\b|\s)", re.IGNORECASE
)


logger = logging.getLogger(__name__)


class CotizacionViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """CotizacionViewSet."""

    queryset = (
        Cotizacion.objects.select_related("cliente", "consultor")
        .prefetch_related("items")
        .order_by("-fecha_emision")
    )
    serializer_class = CotizacionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def convertir_a_venta(self, request, pk=None):
        """Convierte la cotización en una venta"""
        cotizacion = self.get_object()

        try:
            venta = cotizacion.convertir_a_venta()
            return Response(
                {
                    "message": "Cotización convertida exitosamente",
                    "venta_id": venta.id_venta,
                    "localizador": venta.localizador,
                }
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def marcar_enviada(self, request, pk=None):
        """Marca la cotización como enviada"""
        cotizacion = self.get_object()
        cotizacion.estado = Cotizacion.EstadoCotizacion.ENVIADA
        cotizacion.fecha_envio = timezone.now()
        cotizacion.email_enviado = True
        cotizacion.save(update_fields=["estado", "fecha_envio", "email_enviado"])

        return Response({"message": "Cotización marcada como enviada"})

    @action(detail=True, methods=["post"])
    def marcar_vista(self, request, pk=None):
        """Marca la cotización como vista por el cliente"""
        cotizacion = self.get_object()
        if cotizacion.estado == Cotizacion.EstadoCotizacion.ENVIADA:
            cotizacion.estado = Cotizacion.EstadoCotizacion.VISTA
            cotizacion.fecha_vista = timezone.now()
            cotizacion.save(update_fields=["estado", "fecha_vista"])

        return Response({"message": "Cotización marcada como vista"})

    @action(detail=True, methods=["get"])
    def preview_html(self, request, pk=None):
        """Visualizar cotización en HTML"""
        cotizacion = self.get_object()
        return render(request, "cotizaciones/plantilla_cotizacion.html", {"cotizacion": cotizacion})

    @action(detail=True, methods=["get"])
    def preview_pdf(self, request, pk=None):
        """Visualizar/Descargar cotización en PDF"""
        cotizacion = self.get_object()
        try:
            pdf_bytes = generar_pdf_cotizacion(cotizacion)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            filename = f"Cotizacion_{cotizacion.numero_cotizacion}.pdf"
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ItemCotizacionViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """ItemCotizacionViewSet."""

    queryset = ItemCotizacion.objects.select_related("cotizacion").all()
    serializer_class = ItemCotizacionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """perform_create."""
        item = serializer.save()
        item.cotizacion.calcular_total()

    def perform_update(self, serializer):
        """perform_update."""
        item = serializer.save()
        item.cotizacion.calcular_total()

    def perform_destroy(self, instance):
        """perform_destroy."""
        cotizacion = instance.cotizacion
        instance.delete()
        cotizacion.calcular_total()


# --- VISTAS STANDARD (SSR) ---


class CotizacionDashboardView(SaaSMixin, LoginRequiredMixin, ListView):
    """CotizacionDashboardView."""

    model = Cotizacion
    template_name = "core/erp/cotizaciones/dashboard.html"
    context_object_name = "cotizaciones"
    paginate_by = 20

    def get_queryset(self):
        """get_queryset."""
        queryset = Cotizacion.objects.select_related("cliente", "moneda").order_by("-fecha_emision")
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(numero_cotizacion__icontains=q)
                | Q(cliente__nombres__icontains=q)
                | Q(cliente__apellidos__icontains=q)
            )
        estado = self.request.GET.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        context["total_cotizaciones"] = Cotizacion.objects.count()
        context["cotizaciones_pendientes"] = Cotizacion.objects.filter(estado="BOR").count()
        context["cotizaciones_enviadas"] = Cotizacion.objects.filter(estado="ENV").count()
        return context


class CotizacionDetailView(SaaSMixin, LoginRequiredMixin, DetailView):
    """CotizacionDetailView."""

    model = Cotizacion
    template_name = "core/erp/cotizaciones/detalle.html"
    context_object_name = "cotizacion"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items_cotizacion.select_related(
            "producto_servicio", "moneda"
        ).all()
        return context


class CotizacionCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    """CotizacionCreateView."""

    model = Cotizacion
    form_class = CotizacionForm
    template_name = "core/erp/cotizaciones/crear_cotizacion_swiss.html"
    success_url = reverse_lazy("bookings:cotizacion_dashboard")

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["items_formset"] = ItemCotizacionFormSet(self.request.POST)
        else:
            context["items_formset"] = ItemCotizacionFormSet()
        return context

    def form_valid(self, form):
        """form_valid."""
        context = self.get_context_data()
        items_formset = context["items_formset"]
        with transaction.atomic():
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
                self.object.calcular_total()
            else:
                return self.form_invalid(form)
        messages.success(
            self.request, f"Cotización {self.object.numero_cotizacion} creada exitosamente."
        )
        return super().form_valid(form)


class CotizacionUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    """CotizacionUpdateView."""

    model = Cotizacion
    form_class = CotizacionForm
    template_name = "core/erp/cotizaciones/crear_cotizacion_swiss.html"

    def get_success_url(self):
        """get_success_url."""
        return reverse_lazy("bookings:cotizacion_detalle", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["items_formset"] = ItemCotizacionFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["items_formset"] = ItemCotizacionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        """form_valid."""
        context = self.get_context_data()
        items_formset = context["items_formset"]
        with transaction.atomic():
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
                self.object.calcular_total()
            else:
                return self.form_invalid(form)
        messages.success(
            self.request, f"Cotización {self.object.numero_cotizacion} actualizada exitosamente."
        )
        return super().form_valid(form)


class CotizacionStatusView(SaaSMixin, LoginRequiredMixin, View):
    """CotizacionStatusView."""

    def post(self, request, pk):
        """post."""
        cotizacion = get_object_or_404(Cotizacion, pk=pk, agencia=request.agencia)
        nuevo_estado = request.POST.get("nuevo_estado")
        estado_anterior = cotizacion.estado
        cotizacion.estado = nuevo_estado

        if nuevo_estado == Cotizacion.EstadoCotizacion.ENVIADA:
            from django.utils import timezone

            cotizacion.fecha_envio = timezone.now()
            cotizacion.email_enviado = True

        cotizacion.save()

        if nuevo_estado == Cotizacion.EstadoCotizacion.ENVIADA:
            _enviar_cotizacion_whatsapp(cotizacion, request)
        elif nuevo_estado == Cotizacion.EstadoCotizacion.RECHAZADA:
            _notificar_cotizacion_rechazada(cotizacion, estado_anterior)

        messages.success(request, f"Estado actualizado a {cotizacion.get_estado_display()}.")
        return redirect("bookings:cotizacion_detalle", pk=pk)


class CotizacionPDFView(SaaSMixin, LoginRequiredMixin, View):
    """CotizacionPDFView."""

    def get(self, request, pk):
        """get."""
        cotizacion = get_object_or_404(Cotizacion, pk=pk, agencia=request.agencia)
        try:
            pdf_bytes = generar_pdf_cotizacion(cotizacion)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            filename = f"Cotizacion_{cotizacion.numero_cotizacion}.pdf"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            messages.error(request, f"Error generando PDF: {str(e)}")
            return redirect("bookings:cotizacion_detalle", pk=pk)


class CotizacionConvertirView(SaaSMixin, LoginRequiredMixin, View):
    """CotizacionConvertirView."""

    def post(self, request, pk):
        """post."""
        cotizacion = get_object_or_404(Cotizacion, pk=pk, agencia=request.agencia)
        try:
            with transaction.atomic():
                venta = cotizacion.convertir_a_venta()
                messages.success(request, f"Venta generada exitosamente: {venta.localizador}")
                return redirect("bookings:venta_detail", pk=venta.pk)
        except Exception as e:
            messages.error(request, f"Error al convertir a venta: {str(e)}")
        return redirect("bookings:cotizacion_detalle", pk=pk)


class CotizacionHTMXCalculateTotalsView(SaaSMixin, LoginRequiredMixin, View):
    """CotizacionHTMXCalculateTotalsView."""

    def post(self, request, *args, **kwargs):
        """post."""
        subtotal = 0
        impuestos = 0
        total_forms = int(request.POST.get("items_cotizacion-TOTAL_FORMS", 0))
        for i in range(total_forms):
            if request.POST.get(f"items_cotizacion-{i}-DELETE") == "on":
                continue
            try:
                qty = float(request.POST.get(f"items_cotizacion-{i}-cantidad", 0))
                price = float(request.POST.get(f"items_cotizacion-{i}-precio_unitario", 0))
                tax = float(request.POST.get(f"items_cotizacion-{i}-impuestos_item", 0))
                subtotal += qty * price
                impuestos += qty * tax
            except ValueError:
                pass

        moneda_id = request.POST.get("moneda")
        moneda_symbol = "$"
        if moneda_id:
            try:
                from apps.common.models import Moneda

                moneda = Moneda.objects.get(pk=moneda_id)
                moneda_symbol = moneda.simbolo or moneda.codigo_iso
            except Exception as e:
                logger.debug("Ignored exception fetching currency symbol: %s", e)

        return render(
            request,
            "core/erp/cotizaciones/partials/_summary.html",
            {
                "subtotal": subtotal,
                "impuestos": impuestos,
                "total": subtotal + impuestos,
                "moneda_symbol": moneda_symbol,
            },
        )


class CotizacionHTMXAddItemView(LoginRequiredMixin, View):
    """CotizacionHTMXAddItemView."""

    def get(self, request, *args, **kwargs):
        """get."""
        index = int(request.GET.get("index", 0))
        formset = ItemCotizacionFormSet()
        empty_form = formset.empty_form
        empty_form.prefix = f"items_cotizacion-{index}"
        return render(
            request,
            "core/erp/cotizaciones/partials/_item_row_with_oob.html",
            {"form": empty_form, "index": index, "next_index": index + 1},
        )


# --- VISTAS DEL COTIZADOR MÁGICO (GOD MODE) ---


class MagicQuoterView(LoginRequiredMixin, TemplateView):
    """
    Vista principal del Cotizador Mágico. Interfaz Alpine.js + Tailwind.
    """

    template_name = "cotizaciones/magic_quoter.html"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        lead_id = self.request.GET.get("lead_id")
        if lead_id:
            try:
                from apps.crm.models_lead import OportunidadViaje

                context["lead"] = OportunidadViaje.objects.filter(pk=lead_id).first()
            except ImportError:
                pass

        # Inyectar Tasa BCV para Calculadora Integrada
        try:
            tasa = TasaCambioBCV.objects.latest("fecha")
            context["tasa_bcv"] = float(tasa.tasa_bsd_por_usd)
        except Exception:
            context["tasa_bcv"] = 0

        return context


class MagicQuoterAIView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para invocar a Gemini y estructurar el texto crudo de GDS.
    """

    def post(self, request, *args, **kwargs):
        """post."""
        # Manejar tanto peticiones de formulario como JSON
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                raw_text = data.get("raw_text", "")
                agency_fee = data.get("agency_fee", 0)
            except json.JSONDecodeError:
                return JsonResponse({"error": "JSON inválido"}, status=400)
        else:
            raw_text = request.POST.get("raw_text", "")
            agency_fee = request.POST.get("agency_fee", 0)

        # Inicialización de seguridad para evitar NameError
        dates_str = None
        outbound = None
        return_date = None
        destination = "Varios"
        base_price = 0
        final_total = 0
        clean_flights = []
        image_url = ""
        search_query = ""
        ai_output = {}

        if not raw_text:
            return JsonResponse({"error": "No se detectó texto crudo GDS."}, status=400)

        # Instrucción Maestra para Gemini (V2.0 PROMPT: Más vendedora)
        sys_prompt = (
            "Eres el motor Obsidian AI de TravelHub. Analiza el texto GDS y devuelve un JSON ESTRICTO con:\n"
            "- destination: nombre completo de la ciudad destino principal (ej: 'Shanghai', 'Madrid').\n"
            "- destination_description: una frase corta, inspiradora y formal para el cliente que describa el destino (ej: 'Descubra la magia milenaria de Shanghai' o 'Disfrute de la elegancia y cultura de Madrid').\n"
            "- image_search_query: una frase en inglés para buscar una imagen de alta calidad del destino (ej: 'Shanghai skyline night' o 'Madrid city center plaza').\n"
            "- outboundDate y returnDate en formato '20 Abr'.\n"
            "- flights: lista de segmentos. Cada uno con:\n"
            "  * airline: NOMBRE COMPLETO de la aerolínea.\n"
            "  * departureDate: fecha del vuelo en formato '20 Abr'.\n"
            "  * departureCode, arrivalCode: códigos IATA (3 letras).\n"
            "  * departureCity, arrivalCity: nombre completo de la ciudad.\n"
            "  * departureTime, arrivalTime: hora HH:MM.\n"
            "  * stops: 'Directo' o 'Con escala'.\n"
            "  * baggage: info de equipaje si existe (ej: '23kg included').\n"
            "- totalPrice: precio numérico total.\n\n"
            "REGLAS DE ORO: Nombres reales SIEMPRE. Tono formal (use 'Le' no 'Te'). No inventes datos que no existan, usa 'No especificado' si falta."
        )

        try:
            logger.debug(f"[MagicQuoter] hit with {len(raw_text)} chars")
            start = time.time()

            data = ai_engine.call_gemini(
                prompt=f"Extract trip details from this GDS text:\n\n{raw_text}",
                system_instruction=sys_prompt,
                response_schema=CotizacionMagicSchema,
            )

            logger.debug(f"[MagicQuoter] Gemini response received in {time.time() - start:.2f}s")
            logger.info(
                f"[MagicQuoter] data type = {type(data).__name__}, has model_dump = {hasattr(data, 'model_dump')}"
            )

            # Aceptar Pydantic v2 (model_dump), Pydantic v1 (dict), o cualquier dict-like
            if not isinstance(data, dict):
                for method_name in ("model_dump", "dict"):
                    converter = getattr(data, method_name, None)
                    if callable(converter):
                        try:
                            data = converter()
                            logger.info(
                                f"[MagicQuoter] {method_name}() ok, new type = {type(data).__name__}"
                            )
                            break
                        except Exception as e_dump:
                            logger.error(f"No se pudo serializar via {method_name}: {e_dump}")
                            return JsonResponse(
                                {"error": "Error serializando respuesta de IA."}, status=500
                            )
                else:
                    logger.error(
                        f"Gemini data is not a dict and has no converter: {type(data)} value={str(data)[:200]}"
                    )
                    return JsonResponse(
                        {
                            "error": "La IA no devolvió datos válidos.",
                            "debug_type": type(data).__name__,
                        },
                        status=500,
                    )

            if not data:
                logger.error("Gemini returned empty data")
                return JsonResponse({"error": "La IA devolvió datos vacíos."}, status=500)

            if "error" in data:
                logger.warning(f"[MagicQuoter] Gemini returned error: {data['error']}")
                return JsonResponse(data, status=400)

            # --- DICCIONARIO DE EMERGENCIA IATA ---
            IATA_MAP = {
                "CCS": "Caracas",
                "IST": "Estambul",
                "PVG": "Shanghai",
                "MAD": "Madrid",
                "BOG": "Bogotá",
                "MIA": "Miami",
                "EZE": "Buenos Aires",
                "CDG": "París",
                "JFK": "Nueva York",
            }

            # --- EXTRACCIÓN HÍBRIDA ---
            raw_flights = data.get("flights", [])
            if not raw_flights:
                segments = re.findall(
                    r"\d+\s+[A-Z0-9]{2}\s+\d+[A-Z]?\s+\d+[A-Z]{3}\s+\d+\s+([A-Z]{3})([A-Z]{3})",
                    raw_text,
                )
                for dep, arr in segments:
                    raw_flights.append(
                        {"departureCode": dep, "arrivalCode": arr, "airline": "Revisar GDS"}
                    )

            # Destino: Si no hay, usar llegada del primer tramo
            destination = data.get("destination")
            dest_description = data.get(
                "destination_description", "Su propuesta de viaje personalizada."
            )
            image_search_query = data.get("image_search_query")

            if not destination and raw_flights:
                first_arrival = raw_flights[0].get("arrivalCode")
                destination = IATA_MAP.get(first_arrival, first_arrival)

            # Precio
            raw_base = data.get("totalPrice") or 0
            try:
                base_price = float(raw_base)
            except (ValueError, TypeError):
                base_price = 0

            if base_price < 100:
                prices = re.findall(
                    r"(?:TOTAL|TKT|USD|FARE)\s*[:]?\s*(\d+(?:\.\d{2})?)", raw_text.upper()
                )
                if prices:
                    base_price = float(prices[-1])

            # Fechas y Rango (Recuperación)
            dates_str = data.get("dates")
            outbound = data.get("outboundDate") or data.get("outbound_date")
            return_date = data.get("returnDate") or data.get("return_date")

            if not outbound and dates_str:
                if " - " in dates_str:
                    parts = dates_str.split(" - ")
                    outbound = parts[0]
                    return_date = parts[1] if len(parts) > 1 else None
                else:
                    outbound = dates_str

            # --- RESOLUCIÓN DE AEROLÍNEAS DESDE CATÁLOGO DE BASE DE DATOS ---
            # Estrategia de 2 capas para máxima precisión:
            # CAPA 1 (Verdad absoluta): extraer código IATA del texto GDS crudo via regex.
            #   Ej: " QL 450" → "QL" → BD → "Laser Airlines"
            # CAPA 2 (Fallback): usar el nombre que devolvió Gemini, si es código de 2 letras.
            # Esto evita que Gemini "alucine" aerolíneas por contexto de ruta (ej: QL→Wingo).
            from apps.automation.parsers.airline_utils import get_airline_name_by_code

            # Pre-extraer todos los códigos de vuelo del texto GDS.
            gds_flight_codes = re_airlines.findall(raw_text)
            # gds_flight_codes[0] → aerolínea del segmento 1
            # gds_flight_codes[1] → aerolínea del segmento 2, etc.

            clean_flights = []
            for idx, f in enumerate(raw_flights):
                dep_code = f.get("departureCode", "???")
                arr_code = f.get("arrivalCode", "???")

                # --- CAPA 1: Código extraído del GDS crudo (fuente de verdad) ---
                # Intentar identificar aerolínea con regex como fallback
                gds_flight_codes = re_airlines.findall(raw_text)
                airline_code = gds_flight_codes[idx] if idx < len(gds_flight_codes) else "YY"

                clean_airline = None
                # Excluir palabras que no son códigos IATA reales
                EXCLUIDOS = {"NO", "HK", "OK", "SS", "SA", "WL", "UC", "UN", "NN"}
                if airline_code not in EXCLUIDOS:
                    nombre_bd = get_airline_name_by_code(airline_code)
                    if nombre_bd:
                        clean_airline = nombre_bd  # ✅ Encontrado en BD

                # --- CAPA 2: Fallback → lo que devolvió Gemini ---
                if not clean_airline:
                    raw_airline = (f.get("airline", "") or "").strip()
                    if len(raw_airline) == 2 and raw_airline.isalpha():
                        # Gemini devolvió código → buscar en BD
                        nombre_bd = get_airline_name_by_code(raw_airline.upper())
                        clean_airline = nombre_bd if nombre_bd else raw_airline
                    else:
                        # Gemini devolvió nombre completo (puede ser hallucination o correcto)
                        clean_airline = raw_airline or "Aerolínea"

                f_clean = {
                    "airline": clean_airline,
                    "departureDate": f.get("departureDate") or f.get("departure_date"),
                    "departureCode": dep_code,
                    "arrivalCode": arr_code,
                    "departureCity": f.get("departureCity") or IATA_MAP.get(dep_code),
                    "arrivalCity": f.get("arrivalCity") or IATA_MAP.get(arr_code),
                    "departureTime": f.get("departureTime", "--:--"),
                    "arrivalTime": f.get("arrivalTime", "--:--"),
                    "stops": f.get("stops", "Directo"),
                    "baggage": f.get("baggage", "1 Maleta"),
                }
                # Imagen de Destino:
                # Priorizar la consulta estructurada que generó la IA (V2.0)
                search_query = image_search_query or data.get("image_search_query") or destination
                image_url = ""
                clean_flights.append(f_clean)

            # Cálculo Final con el Fee (Unificado para JSON y POST)
            try:
                # Ya extrajimos agency_fee al inicio del método
                actual_fee = float(agency_fee)
            except (ValueError, TypeError):
                actual_fee = 50

            final_total = round(float(base_price) + actual_fee, 2)

            from django.conf import settings
            from django.core.cache import cache

            cache_key = f"unsplash_img_{search_query.lower().replace(' ', '_')}"
            image_url = cache.get(cache_key)

            if not image_url:
                unsplash_key = getattr(settings, "UNSPLASH_ACCESS_KEY", "")
                if unsplash_key:
                    try:
                        res = requests.get(
                            f"https://api.unsplash.com/search/photos?query={search_query}&client_id={unsplash_key}&per_page=1",
                            timeout=3,
                        )
                        if res.status_code == 200:
                            img_data = res.json()
                            if img_data.get("results"):
                                image_url = img_data["results"][0]["urls"]["regular"]
                                cache.set(cache_key, image_url, 86400)
                    except Exception as e:
                        logger.warning(f"Excepción silenciosa capturada: {e}")
            ai_output = {
                "destination": destination,
                "type": data.get("type", "Vuelo"),
                "dates": dates_str or (f"{outbound} - {return_date}" if return_date else outbound),
                "outboundDate": outbound or "Por confirmar",
                "returnDate": return_date,
                "flights": clean_flights,
                "totalPrice": base_price,
                "currency": data.get("currency", "USD"),
                "totalPriceWithFee": final_total,
                "image": image_url,
                "image_search_query": search_query,
                "destination_description": dest_description,
                "notas_ia": data.get("notas_ia", ""),
            }

            return JsonResponse(ai_output)
        except Exception as e:
            logger.error(f"Error en MagicQuoterAIView: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)


class MagicQuoterSaveView(SaaSMixin, LoginRequiredMixin, View):
    """
    Guarda la cotización generada por IA en la base de datos.
    Vincula el Lead si existe y devuelve el UUID para compartir.
    """

    def post(self, request, *args, **kwargs):
        """post."""
        import json

        from django.urls import reverse

        try:
            data = json.loads(request.body)
            lead_id = data.get("lead_id")
            ai_data = data.get("ai_data")
            agency_fee = data.get("agency_fee", 0)
            raw_text = data.get("raw_text", "")
            ai_data.get("parsed_data", {})

            if not ai_data:
                return JsonResponse({"error": "No hay datos de IA para guardar"}, status=400)

            lead = None
            if lead_id:
                from apps.crm.models_lead import OportunidadViaje

                lead = OportunidadViaje.objects.filter(id=lead_id).first()

            # Asegurar Moneda (Evitar nulos en codigo_iso)
            from apps.common.models import Moneda

            currency_raw = ai_data.get("currency") or "USD"
            currency_code = str(currency_raw).strip().upper()[:3]

            if not currency_code:  # Fallback absoluto
                currency_code = "USD"

            moneda, _ = Moneda.objects.get_or_create(
                codigo_iso=currency_code,
                defaults={
                    "nombre": "Dólar Estadounidense" if currency_code == "USD" else currency_code,
                    "simbolo": "$",
                },
            )

            # Estructurar la Cotización
            nombre_final = "Prospecto IA"
            cliente_vinculado = getattr(lead, "cliente", None)
            if cliente_vinculado:
                nombre_final = cliente_vinculado.get_full_name()
            else:
                nombre_final = getattr(lead, "nombre_cliente", "Prospecto (Lead)")

            cotizacion = Cotizacion.objects.create(
                cliente=cliente_vinculado,
                nombre_cliente_manual=nombre_final,
                destino=ai_data.get("destination", "Varios"),
                consultor=request.user,
                moneda=moneda,
                gds_raw_text=raw_text,
                agency_fee=agency_fee,
                metadata_ia=ai_data,
                image_url=ai_data.get("image", ""),
                total_cotizado=ai_data.get("totalPriceWithFee", 0),
                estado="BOR",
            )

            # Asegurar Producto/Servicio (Requerido por DB según error anterior)
            from apps.bookings.models import ProductoServicio

            default_producto = (
                ProductoServicio.objects.filter(tipo_producto="VUE").first()
                or ProductoServicio.objects.first()
            )

            # Guardar items para histórico financiero
            for flight in ai_data.get("flights", []):
                dep = flight.get("departureCode", "???")
                arr = flight.get("arrivalCode", "???")
                f_date = flight.get("departureDate", "")
                ItemCotizacion.objects.create(
                    cotizacion=cotizacion,
                    tipo_item="VUE",
                    producto_servicio=default_producto,
                    descripcion=f"{f_date} | {flight.get('airline')}: {dep} - {arr}",
                    subtotal_item=0,
                    total_item=0,
                    costo=0,
                )

            # Armar la URL absoluta para compartir por WhatsApp
            public_url = request.build_absolute_uri(
                reverse("cotizaciones:public_quote", kwargs={"quote_uuid": str(cotizacion.uuid)})
            )

            # Link de aprobación automática (Pre-rellena un mensaje de vuelta para el cliente)
            # El cliente al darle clic, te enviará a TI (o al que le envió el link) un mensaje de aprobación.
            approval_text = f"✅ ¡Hola! Apruebo la cotización para {cotizacion.destino}. Por favor, procede con la reserva. (Ref: {cotizacion.numero_cotizacion})"
            f"https://wa.me/?text={approval_text.replace(' ', '%20')}"

            # Formatear el itinerario para WhatsApp en texto plano
            flights_text = ""
            for idx, flight in enumerate(ai_data.get("flights", []), start=1):
                dep_code = flight.get("departureCode", "???")
                arr_code = flight.get("arrivalCode", "???")
                airline = flight.get("airline", "Aerolinea")
                f_date = (
                    flight.get("departureDate") or flight.get("departure_date") or "Por confirmar"
                )
                dep_time = flight.get("departureTime") or "--:--"
                arr_time = flight.get("arrivalTime") or "--:--"

                flights_text += f"*Vuelo {idx}: {f_date}*\n"
                flights_text += f"-> Origen: {dep_code} ({dep_time}) | Destino: {arr_code} ({arr_time}) via *{airline}*\n\n"

            # Obtener precio total con fee
            total_price_raw = ai_data.get("totalPriceWithFee") or cotizacion.total_cotizado or 0
            try:
                total_price = float(total_price_raw)
            except (ValueError, TypeError):
                total_price = 0.0

            whatsapp_msg = (
                f"*PROPUESTA DE VIAJE: {cotizacion.destino.upper()}*\n\n"
                f"Hola. Te envio el itinerario personalizado que preparamos para ti:\n\n"
                f"{flights_text}"
                f"*Inversion Total:* ${total_price:,.2f} USD\n\n"
                f"---\n"
                f"*Ver en formato visual:* Si deseas ver fotos y el detalle interactivo de tu propuesta, puedes acceder a tu enlace seguro:\n"
                f"{public_url}\n\n"
                f"Quedo atento a tus comentarios para proceder con la reserva."
            )

            return JsonResponse(
                {
                    "success": True,
                    "uuid": str(cotizacion.uuid),
                    "public_url": public_url,
                    "whatsapp_msg": whatsapp_msg,
                }
            )

        except Exception as e:
            logger.error(f"Error guardando cotización mágica: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)


class PublicQuoteDetailView(DetailView):
    """
    Visualización pública para el cliente final a través del UUID de la cotización.
    Incluye lógica de reparación de metadatos para retrocompatibilidad.
    """

    model = Cotizacion
    template_name = "cotizaciones/public_quote.html"
    context_object_name = "quote"

    def get_object(self, queryset=None):
        """get_object."""
        from core.middleware import system_context

        with system_context():
            return get_object_or_404(Cotizacion, uuid=self.kwargs.get("quote_uuid"))

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        quote = context["quote"]
        meta = quote.metadata_ia or {}

        # --- REPARACIÓN AGRESIVA PARA LINKS ANTIGUOS ---

        # 1. Normalizar Destino (Evitar el "Varios")
        if meta.get("destination") in [None, "Varios", ""]:
            meta["destination"] = meta.get("title") or quote.destino or "Tu Viaje"

        # 2. Normalizar Fechas
        if not meta.get("outboundDate"):
            dates = meta.get("dates", "")
            meta["outboundDate"] = (
                dates.split(" - ")[0] if " - " in dates else (dates or "Por confirmar")
            )

        # 3. Normalizar Vuelos (Mapear 'route' y 'time' a campos nuevos + Ciudades)
        clean_flights = []
        flights_list = meta.get("flights", [])
        for i, f in enumerate(flights_list):
            route = f.get("route", "")
            time_str = f.get("time", "")

            # Códigos
            f["departureCode"] = f.get("departureCode") or (
                route.split(" - ")[0] if " - " in route else "???"
            )
            f["arrivalCode"] = f.get("arrivalCode") or (
                route.split(" - ")[1] if " - " in route else "???"
            )

            # Ciudades (Inferencia Inteligente)
            if not f.get("departureCity") or f.get("departureCity") == "Cargando...":
                if i == 0:
                    f["departureCity"] = "Origen"
                elif i > 0:
                    f["departureCity"] = clean_flights[i - 1].get("arrivalCity", "Escala")

            if not f.get("arrivalCity") or f.get("arrivalCity") == "Cargando...":
                if i == len(flights_list) - 1:
                    f["arrivalCity"] = meta.get("destination", "Destino")
                else:
                    f["arrivalCity"] = "Conexión"

            # Horas
            f["departureTime"] = f.get("departureTime") or (
                time_str.split(" - ")[0] if " - " in time_str else "--:--"
            )
            f["arrivalTime"] = f.get("arrivalTime") or (
                time_str.split(" - ")[1] if " - " in time_str else "--:--"
            )

            # Fecha (Fallback a la fecha de salida del itinerario si falta en el segmento)
            if not f.get("departureDate"):
                f["departureDate"] = meta.get("outboundDate", "Por confirmar")

            clean_flights.append(f)
        meta["flights"] = clean_flights

        # 4. Asegurar que la agencia esté disponible para el branding (Incluso para anónimos)
        if not context.get("current_agency"):
            try:
                from core.models.agencia import UsuarioAgencia

                ua = UsuarioAgencia.objects.filter(usuario=quote.consultor, activo=True).first()
                if ua:
                    context["current_agency"] = ua.agencia
            except Exception as e:
                logger.warning(f"Excepción silenciosa capturada: {e}")
        # 5. Forzar actualización de imagen si el destino era genérico
        img_url = meta.get("image") or ""
        if "unsplash" not in img_url.lower() and "Varios" not in (meta.get("destination") or ""):
            # Solo si no tiene una imagen de Unsplash ya puesta
            search = meta.get("image_search_query") or meta["destination"]
            meta["image_search_query"] = search

        quote.metadata_ia = meta
        return context

    def render_to_response(self, context, **response_kwargs):
        """render_to_response."""
        response = super().render_to_response(context, **response_kwargs)
        quote = context["quote"]
        if quote.estado == Cotizacion.EstadoCotizacion.ENVIADA:
            from django.utils import timezone

            quote.estado = Cotizacion.EstadoCotizacion.VISTA
            quote.fecha_vista = timezone.now()
            quote.save(update_fields=["estado", "fecha_vista"])

            if quote.consultor:
                _notificar_agente_cotizacion_vista(quote)
        return response


def _enviar_cotizacion_whatsapp(cotizacion, request):
    """Envía la cotización al cliente por WhatsApp cuando se marca como ENVIADA"""
    try:
        cliente = cotizacion.cliente
        if not cliente or not cliente.telefono_principal:
            logger.info(f"Cotización {cotizacion.pk} sin cliente o teléfono. Saltando WhatsApp.")
            return

        from apps.communications.services.whatsapp_unified import enviar_whatsapp

        public_url = request.build_absolute_uri(f"/cotizaciones/public/{cotizacion.uuid}/")

        nombre = cliente.get_nombre_completo() or "Viajero"
        consultor_nombre = (
            cotizacion.consultor.get_full_name() or cotizacion.consultor.username
            if cotizacion.consultor
            else "tu asesor"
        )
        simbolo = cotizacion.moneda.simbolo if cotizacion.moneda else "$"

        mensaje = (
            f"¡Hola {nombre}! ✈️\n\n"
            f"Te saluda *{consultor_nombre}* de *TravelHub*.\n\n"
            f"Tengo lista tu propuesta de viaje a *{cotizacion.destino or 'tu próximo destino'}*.\n\n"
            f"💰 *Inversión:* {simbolo} {cotizacion.total_cotizado}\n"
            f"🔗 *Ver Itinerario Completo:* {public_url}\n\n"
            f"¿Qué te parece? Quedo atento si deseas cambios o proceder con la reserva."
        )

        enviar_whatsapp(cliente.telefono_principal, mensaje, agencia=cotizacion.agencia)
        logger.info(f"✅ WhatsApp de cotización enviado: {cotizacion.numero_cotizacion}")
    except Exception as e:
        logger.warning(f"Error enviando cotización por WhatsApp: {e}")


def _notificar_agente_cotizacion_vista(cotizacion):
    """Notifica al agente por Telegram cuando el cliente ve la cotización"""
    try:
        from django.conf import settings

        from apps.common.tasks import send_telegram_task

        chat_id = getattr(settings, "TELEGRAM_GROUP_ID", None)
        if not chat_id:
            return

        cliente_nombre = (
            cotizacion.cliente.get_nombre_completo()
            if cotizacion.cliente
            else cotizacion.nombre_cliente_manual or "N/A"
        )

        msg = (
            f"👁️ <b>Cotización Vista por Cliente</b>\n\n"
            f"📋 <b>{cotizacion.numero_cotizacion}</b>\n"
            f"👤 Cliente: {cliente_nombre}\n"
            f"🌍 Destino: {cotizacion.destino}\n"
            f"💰 Total: {cotizacion.moneda.simbolo if cotizacion.moneda else '$'} {cotizacion.total_cotizado}\n\n"
            f"<i>El cliente ha abierto tu propuesta.</i>"
        )

        send_telegram_task.delay(message=msg, chat_id=chat_id)
    except Exception as e:
        logger.warning(f"Error notificando agente de cotización vista: {e}")


def _notificar_cotizacion_rechazada(cotizacion, estado_anterior):
    """Notifica al agente cuando una cotización es rechazada"""
    try:
        from django.conf import settings

        from apps.common.tasks import send_telegram_task

        chat_id = getattr(settings, "TELEGRAM_GROUP_ID", None)
        if not chat_id:
            return

        cliente_nombre = (
            cotizacion.cliente.get_nombre_completo()
            if cotizacion.cliente
            else cotizacion.nombre_cliente_manual or "N/A"
        )

        msg = (
            f"❌ <b>Cotización Rechazada</b>\n\n"
            f"📋 <b>{cotizacion.numero_cotizacion}</b>\n"
            f"👤 Cliente: {cliente_nombre}\n"
            f"🌍 Destino: {cotizacion.destino}\n"
            f"💰 Total: {cotizacion.moneda.simbolo if cotizacion.moneda else '$'} {cotizacion.total_cotizado}\n\n"
            f"<i>Considera hacer un follow-up con el cliente.</i>"
        )

        send_telegram_task.delay(message=msg, chat_id=chat_id)
    except Exception as e:
        logger.warning(f"Error notificando cotización rechazada: {e}")

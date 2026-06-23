import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from rest_framework import filters, permissions, viewsets

from apps.bookings.models import Proveedor
from core.api import HtmxResponseMixin, SaaSMixin
from core.api.mixins.tenant import TenantViewSetMixin
from core.serializers import ProveedorSerializer

logger = logging.getLogger(__name__)


class ProveedorListView(HtmxResponseMixin, SaaSMixin, LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = "core/erp/proveedores/list.html"
    htmx_template_name = "common/partials/proveedores_htmx.html"
    context_object_name = "proveedores"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super().get_queryset().select_related("ciudad", "ciudad__pais").order_by("nombre")
        )

        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q)
                | Q(alias__icontains=q)
                | Q(rif__icontains=q)
                | Q(contacto_nombre__icontains=q)
                | Q(tipo_proveedor__icontains=q)
            )

        tipo = self.request.GET.get("tipo")
        if tipo:
            queryset = queryset.filter(tipo_proveedor=tipo)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "configuracion"
        # Intenta obtener choices de varias fuentes para compatibilidad
        if hasattr(Proveedor, "TipoProveedorChoices"):
            context["tipos_proveedor"] = Proveedor.TipoProveedorChoices.choices
        elif hasattr(Proveedor, "TipoProveedor"):
            context["tipos_proveedor"] = Proveedor.TipoProveedor.choices
        return context


class ProveedorFormMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for _field_name, field in form.fields.items():
            input_type = getattr(field.widget, "input_type", None)
            if input_type == "checkbox":
                # Los checkboxes usan estilos por defecto del navegador/tema, no input-base
                field.widget.attrs["class"] = (
                    "h-5 w-5 rounded border-border-color text-primary focus:ring-primary"
                )
            else:
                field.widget.attrs["class"] = "input-base"
        return form


class ProveedorCreateView(SaaSMixin, LoginRequiredMixin, ProveedorFormMixin, CreateView):
    model = Proveedor
    template_name = "core/erp/proveedores/form.html"
    fields = [
        "nombre",
        "alias",
        "rif",
        "tipo_proveedor",
        "nivel_proveedor",
        "contacto_nombre",
        "contacto_email",
        "contacto_telefono",
        "direccion",
        "ciudad",
        "notas",
        "numero_cuenta_agencia",
        "condiciones_pago",
        "datos_bancarios",
        "fee_nacional",
        "fee_internacional",
        "activo",
        "iata",
        "seudo_sabre",
        "office_id_kiu",
        "office_id_amadeus",
        "office_id_travelport",
        "office_id_hotelbeds",
        "office_id_expedia",
    ]
    success_url = reverse_lazy("bookings:proveedor_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "configuracion"
        context["title"] = "Nuevo Proveedor"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Proveedor creado exitosamente.")
        return super().form_valid(form)


class ProveedorUpdateView(SaaSMixin, LoginRequiredMixin, ProveedorFormMixin, UpdateView):
    model = Proveedor
    template_name = "core/erp/proveedores/form.html"
    fields = [
        "nombre",
        "alias",
        "rif",
        "tipo_proveedor",
        "nivel_proveedor",
        "contacto_nombre",
        "contacto_email",
        "contacto_telefono",
        "direccion",
        "ciudad",
        "notas",
        "numero_cuenta_agencia",
        "condiciones_pago",
        "datos_bancarios",
        "fee_nacional",
        "fee_internacional",
        "activo",
        "iata",
        "seudo_sabre",
        "office_id_kiu",
        "office_id_amadeus",
        "office_id_travelport",
        "office_id_hotelbeds",
        "office_id_expedia",
    ]
    success_url = reverse_lazy("bookings:proveedor_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "configuracion"
        context["title"] = f"Editar Proveedor: {self.object.nombre}"
        context["proveedor_id"] = self.object.pk

        # Serializar monedas disponibles para el frontend (Útil para configuraciones de comisión)
        try:
            from rest_framework import serializers

            from apps.bookings.models import ProductoServicio
            from apps.common.models import Moneda

            class MonedaSerializer(serializers.ModelSerializer):
                class Meta:
                    model = Moneda
                    fields = ["id_moneda", "nombre", "codigo_iso", "simbolo", "es_moneda_local"]

            context["monedas_json"] = MonedaSerializer(Moneda.objects.all(), many=True).data
            context["tipos_servicio_choices"] = [
                {"id": c[0], "label": c[1]} for c in ProductoServicio.TipoProductoChoices.choices
            ]
        except (ImportError, AttributeError, serializers.SerializerError) as e:
            logger.warning("No se pudo serializar monedas/tipos para ProveedorUpdateView: %s", e)

        return context

    def form_valid(self, form):
        messages.success(self.request, "Proveedor actualizado exitosamente.")
        return super().form_valid(form)


class ProveedorDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = Proveedor
    template_name = "core/erp/catalogos/proveedores_confirm_delete.html"
    success_url = reverse_lazy("bookings:proveedor_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Proveedor eliminado correctamente.")
        return super().delete(request, *args, **kwargs)


class ProveedorViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Proveedor.objects.all().order_by("nombre")
    serializer_class = ProveedorSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ["nombre", "contacto_nombre", "contacto_email", "rif"]

"""Vistas (views) de la aplicación common.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.models import Aerolinea, Ciudad, Moneda, Pais
from core.api import HtmxResponseMixin, SaaSMixin, get_user_active_agency


def _get_model(app_label: str, model_name: str):
    """Lazily resolve a model at call time to avoid circular/startup issues."""
    from django.apps import apps  # noqa: PLC0415

    return apps.get_model(app_label, model_name)


class CatalogosCenterView:
    """Vista para gestionar catalogoscenter. Uso: instanciar según necesidad del dominio.
    """
    model = Moneda  # Dummy model to satisfy ListView
    template_name = "core/erp/catalogos/center.html"

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "configuracion"
        return context


class AerolineaListView:
    """Vista para gestionar aerolinealist. Uso: instanciar según necesidad del dominio.
    """
    model = Aerolinea
    template_name = "core/erp/catalogos/aerolineas_list.html"
    htmx_template_name = "common/partials/aerolineas_htmx.html"
    context_object_name = "aerolineas"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        q = self.request.GET.get("q")
        queryset = Aerolinea.objects.all().order_by("nombre")
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_iata__icontains=q))
        return queryset


class AerolineaCreateView:
    """Vista para gestionar aerolineacreate. Uso: instanciar según necesidad del dominio.
    """
    model = Aerolinea
    template_name = "core/erp/catalogos/aerolinea_form.html"
    fields = ["nombre", "codigo_iata", "activa"]
    success_url = reverse_lazy("common_admin:aerolinea_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Aerolínea creada exitosamente.")
        return super().form_valid(form)


class AerolineaUpdateView:
    """Vista para gestionar aerolineaupdate. Uso: instanciar según necesidad del dominio.
    """
    model = Aerolinea
    template_name = "core/erp/catalogos/aerolinea_form.html"
    fields = ["nombre", "codigo_iata", "activa"]
    success_url = reverse_lazy("common_admin:aerolinea_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Aerolínea actualizada exitosamente.")
        return super().form_valid(form)


class AerolineaDeleteView:
    """Vista para gestionar aerolineadelete. Uso: instanciar según necesidad del dominio.
    """
    model = Aerolinea
    template_name = "core/erp/catalogos/aerolinea_confirm_delete.html"
    success_url = reverse_lazy("common_admin:aerolinea_list")

    def delete(self, request, *args, **kwargs):
        # delete: Elimina el objeto de la base de datos. Args: None. Returns: None.
        messages.success(self.request, "Aerolínea eliminada correctamente.")
        return super().delete(request, *args, **kwargs)


class ProductoServicioListView:
    """Vista para gestionar productoserviciolist. Uso: instanciar según necesidad del dominio.
    """
    model = None
    template_name = "core/erp/catalogos/productos_list.html"
    htmx_template_name = "common/partials/productos_htmx.html"
    context_object_name = "productos"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        ProductoServicio = _get_model("bookings", "ProductoServicio")
        q = self.request.GET.get("q")
        queryset = ProductoServicio.objects.select_related(
            "proveedor_principal", "moneda_referencial"
        ).order_by("nombre")
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_interno__icontains=q))
        return queryset


class PaisListView:
    """Vista para gestionar paislist. Uso: instanciar según necesidad del dominio.
    """
    model = Pais
    template_name = "core/erp/catalogos/geografia_list.html"
    htmx_template_name = "common/partials/paises_htmx.html"
    context_object_name = "paises"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        q = self.request.GET.get("q")
        queryset = Pais.objects.all().order_by("nombre")
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_iso__icontains=q))
        return queryset


class GeografiaListView(HtmxResponseMixin, SaaSMixin, LoginRequiredMixin, ListView):
    """Vista combinada para Geografía (Países y Ciudades)."""

    model = Ciudad
    template_name = "core/erp/catalogos/geografia_list.html"
    htmx_template_name = "common/partials/geografia_htmx.html"
    context_object_name = "ciudades"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        q = self.request.GET.get("q")
        queryset = Ciudad.objects.select_related("pais").all().order_by("pais__nombre", "nombre")
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) | Q(pais__nombre__icontains=q) | Q(codigo_iata__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["paises_count"] = Pais.objects.count()
        return context


# --- Vistas CRUD para Pais ---
class PaisCreateView:
    """Vista para gestionar paiscreate. Uso: instanciar según necesidad del dominio.
    """
    model = Pais
    template_name = "core/erp/catalogos/pais_form.html"
    fields = ["nombre", "codigo_iso_2", "codigo_iso_3", "prefijo_telefonico"]
    success_url = reverse_lazy("common_admin:geografia_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "País creado exitosamente.")
        return super().form_valid(form)


class PaisUpdateView:
    """Vista para gestionar paisupdate. Uso: instanciar según necesidad del dominio.
    """
    model = Pais
    template_name = "core/erp/catalogos/pais_form.html"
    fields = ["nombre", "codigo_iso_2", "codigo_iso_3", "prefijo_telefonico"]
    success_url = reverse_lazy("common_admin:geografia_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "País actualizado exitosamente.")
        return super().form_valid(form)


class PaisDeleteView:
    """Vista para gestionar paisdelete. Uso: instanciar según necesidad del dominio.
    """
    model = Pais
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("common_admin:geografia_list")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["object_name"] = "País"
        context["object_instance"] = self.object.nombre
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        # delete: Elimina el objeto de la base de datos. Args: None. Returns: None.
        messages.success(self.request, "País eliminado correctamente.")
        return super().delete(request, *args, **kwargs)


# --- Vistas CRUD para Ciudad ---
class CiudadCreateView:
    """Vista para gestionar ciudadcreate. Uso: instanciar según necesidad del dominio.
    """
    model = Ciudad
    template_name = "core/erp/catalogos/ciudad_form.html"
    fields = ["nombre", "pais", "codigo_iata", "region_estado"]
    success_url = reverse_lazy("common_admin:geografia_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Ciudad creada exitosamente.")
        return super().form_valid(form)


class CiudadUpdateView:
    """Vista para gestionar ciudadupdate. Uso: instanciar según necesidad del dominio.
    """
    model = Ciudad
    template_name = "core/erp/catalogos/ciudad_form.html"
    fields = ["nombre", "pais", "codigo_iata", "region_estado"]
    success_url = reverse_lazy("common_admin:geografia_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Ciudad actualizada exitosamente.")
        return super().form_valid(form)


class CiudadDeleteView:
    """Vista para gestionar ciudaddelete. Uso: instanciar según necesidad del dominio.
    """
    model = Ciudad
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("common_admin:geografia_list")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Ciudad"
        context["object_instance"] = self.object.nombre
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        # delete: Elimina el objeto de la base de datos. Args: None. Returns: None.
        messages.success(self.request, "Ciudad eliminada correctamente.")
        return super().delete(request, *args, **kwargs)


class TipoCambioListView:
    """Vista para gestionar tipocambiolist. Uso: instanciar según necesidad del dominio.
    """
    model = None
    template_name = "core/config/tasas_list.html"
    htmx_template_name = "common/partials/tasas_htmx.html"
    context_object_name = "tasas"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        TipoCambio = _get_model("finance", "TipoCambio")
        return TipoCambio.objects.select_related("moneda_origen", "moneda_destino").order_by(
            "-fecha_efectiva", "moneda_origen__codigo_iso"
        )

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "configuracion"
        context["title"] = "Tasas de Cambio"
        recientes = []
        pares_vistos = set()
        for t in self.get_queryset():
            par = (t.moneda_origen_id, t.moneda_destino_id)
            if par not in pares_vistos:
                recientes.append(t)
                pares_vistos.add(par)
            if len(recientes) >= 5:
                break
        context["tasas_actuales"] = recientes
        try:
            from apps.finance.models_stubs import TasaCambio
            p2p = TasaCambio.objects.filter(moneda="P2P").order_by("-fecha").first()
            context["tasa_p2p"] = p2p.monto if p2p else None
        except Exception:
            context["tasa_p2p"] = None
        return context


class TipoCambioCreateView:
    """Vista para gestionar tipocambiocreate. Uso: instanciar según necesidad del dominio.
    """
    model = None
    template_name = "core/config/tasas_form.html"
    fields = ["moneda_origen", "moneda_destino", "fecha_efectiva", "tasa_conversion"]
    success_url = reverse_lazy("core:tasas_list")

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        return _get_model("finance", "TipoCambio").objects.all()

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = (
                "w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:ring-primary focus:border-primary"
            )
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Tasa de cambio registrada exitosamente.")
        return super().form_valid(form)


class SincronizarTasasActionView:
    """Vista para gestionar sincronizartasasaction. Uso: instanciar según necesidad del dominio.
    """
    def post(self, request):
        # post: Post. Args: según implementación. Returns: según implementación.
        try:
            from django.utils.module_loading import import_string

            sinc_func = import_string("apps.contabilidad.views_tasas.sincronizar_tasas_manual")
            sinc_func(request)
            # El mensaje de éxito ya lo pone sincronizar_tasas_manual
        except Exception as e:
            messages.error(request, f"Error al sincronizar: {str(e)}")
        return redirect("core:tasas_list")


# --- Comisiones ---


class ComisionProveedorServicioListView:
    """Vista para gestionar comisionproveedorserviciolist. Uso: instanciar según necesidad del dominio.
    """
    model = None
    template_name = "core/erp/catalogos/comisiones_list.html"
    context_object_name = "comisiones"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        ComisionProveedorServicio = _get_model("bookings", "ComisionProveedorServicio")
        queryset = (
            ComisionProveedorServicio.objects.select_related("proveedor", "moneda")
            .all()
            .order_by("proveedor__nombre", "tipo_servicio")
        )
        agencia = get_user_active_agency(self.request.user)
        if agencia:
            queryset = queryset.filter(agencia=agencia)
        proveedor_id = self.request.GET.get("proveedor")
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        return queryset

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        qs = _get_model("bookings", "Proveedor").objects.all().order_by("nombre")
        if hasattr(self.request, "agencia") and self.request.agencia:
            qs = qs.filter(agencia=self.request.agencia)
        context["proveedores"] = qs
        context["proveedor_id"] = self.request.GET.get("proveedor")
        return context


class ComisionProveedorServicioCreateView:
    """Vista para gestionar comisionproveedorserviciocreate. Uso: instanciar según necesidad del dominio.
    """
    model = None
    template_name = "core/erp/catalogos/comisiones_form.html"
    fields = [
        "proveedor",
        "tipo_servicio",
        "comision_porcentaje",
        "comision_monto_fijo",
        "moneda",
        "notas",
        "activo",
    ]
    success_url = reverse_lazy("core:comisiones_list")

    def get_initial(self):
        # get_initial: Obtiene/recupera initial. Args: según implementación. Returns: dato solicitado.
        initial = super().get_initial()
        proveedor_id = self.request.GET.get("proveedor")
        if proveedor_id:
            initial["proveedor"] = proveedor_id
        return initial

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = (
                "w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 transition-all"
            )
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Regla de comisión creada exitosamente.")
        return super().form_valid(form)


class ComisionProveedorServicioUpdateView:
    """Vista para gestionar comisionproveedorservicioupdate. Uso: instanciar según necesidad del dominio.
    """
    model = None
    template_name = "core/erp/catalogos/comisiones_form.html"
    fields = [
        "proveedor",
        "tipo_servicio",
        "comision_porcentaje",
        "comision_monto_fijo",
        "moneda",
        "notas",
        "activo",
    ]
    success_url = reverse_lazy("core:comisiones_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = (
                "w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 transition-all"
            )
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Regla de comisión actualizada exitosamente.")
        return super().form_valid(form)


class ComisionProveedorServicioDeleteView:
    """Vista para gestionar comisionproveedorserviciodelete. Uso: instanciar según necesidad del dominio.
    """
    model = None
    template_name = "core/erp/catalogos/comisiones_confirm_delete.html"
    success_url = reverse_lazy("core:comisiones_list")

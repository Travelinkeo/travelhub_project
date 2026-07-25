# apps/bookings/views/admin_views.py
"""Vistas (views) de la aplicación bookings.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.bookings.models import CruceroReserva, ProductoServicio
from core.api import SaaSMixin

# --- Vistas para ProductoServicio ---


class ProductoServicioListView:
    """Vista para gestionar productoserviciolist. Uso: instanciar según necesidad del dominio.
    """
    model = ProductoServicio
    template_name = "bookings/admin/productoservicio_list.html"
    context_object_name = "productos"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        q = self.request.GET.get("q")
        queryset = ProductoServicio.objects.select_related(
            "proveedor_principal", "moneda_referencial"
        ).order_by("nombre")
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_interno__icontains=q))
        return queryset


class ProductoServicioCreateView:
    """Vista para gestionar productoserviciocreate. Uso: instanciar según necesidad del dominio.
    """
    model = ProductoServicio
    template_name = "bookings/admin/productoservicio_form.html"
    fields = [
        "nombre",
        "codigo_interno",
        "tipo_producto",
        "proveedor_principal",
        "moneda_referencial",
        "precio_base",
        "activo",
    ]
    success_url = reverse_lazy("bookings_admin:productoservicio_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Producto/Servicio creado exitosamente.")
        return super().form_valid(form)


class ProductoServicioUpdateView:
    """Vista para gestionar productoservicioupdate. Uso: instanciar según necesidad del dominio.
    """
    model = ProductoServicio
    template_name = "bookings/admin/productoservicio_form.html"
    fields = [
        "nombre",
        "codigo_interno",
        "tipo_producto",
        "proveedor_principal",
        "moneda_referencial",
        "precio_base",
        "activo",
    ]
    success_url = reverse_lazy("bookings_admin:productoservicio_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Producto/Servicio actualizado exitosamente.")
        return super().form_valid(form)


class ProductoServicioDeleteView:
    """Vista para gestionar productoserviciodelete. Uso: instanciar según necesidad del dominio.
    """
    model = ProductoServicio
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("bookings_admin:productoservicio_list")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Producto/Servicio"
        context["object_instance"] = self.object.nombre
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        # delete: Elimina el objeto de la base de datos. Args: None. Returns: None.
        messages.success(self.request, "Producto/Servicio eliminado correctamente.")
        return super().delete(request, *args, **kwargs)


# --- Vistas para CruceroReserva ---


class CruceroReservaListView:
    """Vista para gestionar cruceroreservalist. Uso: instanciar según necesidad del dominio.
    """
    model = CruceroReserva
    template_name = "bookings/admin/cruceroreserva_list.html"
    context_object_name = "cruceros"
    paginate_by = 30

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        q = self.request.GET.get("q")
        queryset = CruceroReserva.objects.select_related("venta", "proveedor", "moneda").order_by(
            "-fecha_embarque"
        )
        if q:
            queryset = queryset.filter(
                Q(nombre_crucero__icontains=q)
                | Q(naviera__icontains=q)
                | Q(venta__localizador__icontains=q)
            )
        return queryset


class CruceroReservaCreateView:
    """Vista para gestionar cruceroreservacreate. Uso: instanciar según necesidad del dominio.
    """
    model = CruceroReserva
    template_name = "bookings/admin/cruceroreserva_form.html"
    fields = [
        "venta",
        "proveedor",
        "nombre_crucero",
        "naviera",
        "fecha_embarque",
        "fecha_desembarque",
        "cabina",
        "pasajeros",
        "precio_total",
        "moneda",
        "notas",
    ]
    success_url = reverse_lazy("bookings_admin:cruceroreserva_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Reserva de Crucero creada exitosamente.")
        return super().form_valid(form)


class CruceroReservaUpdateView:
    """Vista para gestionar cruceroreservaupdate. Uso: instanciar según necesidad del dominio.
    """
    model = CruceroReserva
    template_name = "bookings/admin/cruceroreserva_form.html"
    fields = [
        "venta",
        "proveedor",
        "nombre_crucero",
        "naviera",
        "fecha_embarque",
        "fecha_desembarque",
        "cabina",
        "pasajeros",
        "precio_total",
        "moneda",
        "notas",
    ]
    success_url = reverse_lazy("bookings_admin:cruceroreserva_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Reserva de Crucero actualizada exitosamente.")
        return super().form_valid(form)


class CruceroReservaDeleteView:
    """Vista para gestionar cruceroreservadelete. Uso: instanciar según necesidad del dominio.
    """
    model = CruceroReserva
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("bookings_admin:cruceroreserva_list")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Reserva de Crucero"
        context["object_instance"] = f"{self.object.nombre_crucero} ({self.object.naviera})"
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        # delete: Elimina el objeto de la base de datos. Args: None. Returns: None.
        messages.success(self.request, "Reserva de Crucero eliminada correctamente.")
        return super().delete(request, *args, **kwargs)

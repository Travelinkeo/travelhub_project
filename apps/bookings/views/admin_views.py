# apps/bookings/views/admin_views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.bookings.models import CruceroReserva, ProductoServicio
from core.api import SaaSMixin

# --- Vistas para ProductoServicio ---


class ProductoServicioListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = ProductoServicio
    template_name = "bookings/admin/productoservicio_list.html"
    context_object_name = "productos"
    paginate_by = 30

    def get_queryset(self):
        q = self.request.GET.get("q")
        queryset = ProductoServicio.objects.select_related(
            "proveedor_principal", "moneda_referencial"
        ).order_by("nombre")
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_interno__icontains=q))
        return queryset


class ProductoServicioCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
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
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Producto/Servicio creado exitosamente.")
        return super().form_valid(form)


class ProductoServicioUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
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
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Producto/Servicio actualizado exitosamente.")
        return super().form_valid(form)


class ProductoServicioDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = ProductoServicio
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("bookings_admin:productoservicio_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Producto/Servicio"
        context["object_instance"] = self.object.nombre
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Producto/Servicio eliminado correctamente.")
        return super().delete(request, *args, **kwargs)


# --- Vistas para CruceroReserva ---


class CruceroReservaListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = CruceroReserva
    template_name = "bookings/admin/cruceroreserva_list.html"
    context_object_name = "cruceros"
    paginate_by = 30

    def get_queryset(self):
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


class CruceroReservaCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
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
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Reserva de Crucero creada exitosamente.")
        return super().form_valid(form)


class CruceroReservaUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
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
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Reserva de Crucero actualizada exitosamente.")
        return super().form_valid(form)


class CruceroReservaDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = CruceroReserva
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("bookings_admin:cruceroreserva_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Reserva de Crucero"
        context["object_instance"] = f"{self.object.nombre_crucero} ({self.object.naviera})"
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Reserva de Crucero eliminada correctamente.")
        return super().delete(request, *args, **kwargs)

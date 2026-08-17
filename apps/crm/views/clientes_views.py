from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.common.mixins.export_mixin import ExportMixin
from apps.crm.models import Cliente
from core.api import HtmxResponseMixin, SaaSMixin


class CRMBaseMixin(SaaSMixin, LoginRequiredMixin):
    """CRMBaseMixin."""

    context_object_name = "object"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "crm"
        return context


class ClienteListView(ExportMixin, HtmxResponseMixin, CRMBaseMixin, ListView):
    """ClienteListView."""

    model = Cliente
    template_name = "crm/cliente_list.html"  # Preferring app template
    htmx_template_name = "crm/partials/cliente_list_table.html"
    context_object_name = "clientes"
    paginate_by = 25
    export_fields = [
        "tipo_cliente",
        "nombres",
        "apellidos",
        "cedula_identidad",
        "email",
        "telefono_principal",
        "ciudad__nombre",
    ]
    export_filename = "clientes"

    def get_queryset(self):
        """get_queryset."""
        queryset = (
            super()
            .get_queryset()
            .select_related("ciudad", "nacionalidad")
            .order_by("apellidos", "nombres")
        )
        q = self.request.GET.get("q")
        tipo = self.request.GET.get("tipo")
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q)
                | Q(apellidos__icontains=q)
                | Q(cedula_identidad__icontains=q)
                | Q(nombre_empresa__icontains=q)
                | Q(email__icontains=q)
            )
        if tipo:
            queryset = queryset.filter(tipo_cliente=tipo)
        return queryset

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        from django.utils import timezone

        hoy = timezone.now()
        base_qs = self.get_queryset()
        context["clientes_corp_count"] = base_qs.filter(tipo_cliente="COR").count()
        context["clientes_vip_count"] = base_qs.filter(tipo_cliente="VIP").count()
        context["clientes_nuevos_mes"] = base_qs.filter(
            fecha_registro__year=hoy.year, fecha_registro__month=hoy.month
        ).count()
        context["tipos_cliente"] = Cliente.TipoCliente.choices
        return context


class ClienteDetailView(CRMBaseMixin, DetailView):
    """ClienteDetailView."""

    model = Cliente
    template_name = "crm/cliente_detail.html"
    context_object_name = "cliente"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        from django.apps import apps

        Cotizacion = apps.get_model("cotizaciones", "Cotizacion")

        context["cotizaciones"] = (
            Cotizacion.objects.filter(cliente=self.object)
            .select_related("moneda", "consultor")
            .order_by("-fecha_emision")
        )
        context["movimientos_saldo"] = (
            self.object.movimientos_saldo.filter(is_deleted=False)
            .select_related("moneda", "venta", "registrado_por")
            .order_by("-creado")
        )
        context["saldo_a_favor"] = self.object.saldo_a_favor
        return context


class ClienteCreateView(CRMBaseMixin, CreateView):
    """ClienteCreateView."""

    model = Cliente
    template_name = "crm/cliente_form.html"
    fields = [
        "foto_perfil",
        "tipo_cliente",
        "nombres",
        "apellidos",
        "nombre_empresa",
        "cedula_identidad",
        "email",
        "telefono_principal",
        "nacionalidad",
        "direccion",
        "ciudad",
    ]
    success_url = reverse_lazy("crm:cliente_list")

    def form_valid(self, form):
        """form_valid."""
        messages.success(self.request, "Cliente creado correctamente.")
        return super().form_valid(form)


class ClienteUpdateView(CRMBaseMixin, UpdateView):
    """ClienteUpdateView."""

    model = Cliente
    template_name = "crm/cliente_form.html"
    fields = [
        "foto_perfil",
        "tipo_cliente",
        "nombres",
        "apellidos",
        "nombre_empresa",
        "cedula_identidad",
        "email",
        "telefono_principal",
        "nacionalidad",
        "direccion",
        "ciudad",
    ]

    def get_success_url(self):
        """get_success_url."""
        return reverse_lazy("crm:cliente_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        """form_valid."""
        messages.success(self.request, "Cliente actualizado correctamente.")
        return super().form_valid(form)


class ClienteDeleteView(CRMBaseMixin, DeleteView):
    """ClienteDeleteView."""

    model = Cliente
    success_url = reverse_lazy("crm:cliente_list")
    template_name = "crm/cliente_confirm_delete.html"


class ClienteRecargarSaldoView(CRMBaseMixin, DetailView):
    """Vista HTMX para registrar un depósito / abono a la billetera del cliente."""

    model = Cliente

    def get(self, request, *args, **kwargs):
        cliente = self.get_object()
        from django.shortcuts import render

        return render(request, "crm/partials/recargar_saldo_modal.html", {"cliente": cliente})

    def post(self, request, *args, **kwargs):
        cliente = self.get_object()
        monto = request.POST.get("monto")
        metodo = request.POST.get("metodo", "TRF")
        referencia = request.POST.get("referencia", "")
        descripcion = request.POST.get("descripcion", "")
        comprobante = request.FILES.get("comprobante")

        from django.shortcuts import redirect, render

        from apps.crm.services.wallet_service import WalletClienteService

        try:
            WalletClienteService.recargar_saldo(
                cliente=cliente,
                monto=monto,
                metodo_pago=metodo,
                referencia=referencia,
                descripcion=descripcion,
                comprobante=comprobante,
                usuario=request.user,
            )
            messages.success(request, f"Depósito de ${monto} USD registrado exitosamente.")
            if request.headers.get("HX-Request"):
                from django.http import HttpResponse

                res = HttpResponse()
                res["HX-Refresh"] = "true"
                return res
            return redirect("crm:cliente_detail", pk=cliente.pk)
        except Exception as e:
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "crm/partials/recargar_saldo_modal.html",
                    {"cliente": cliente, "error": str(e)},
                )
            messages.error(request, str(e))
            return redirect("crm:cliente_detail", pk=cliente.pk)

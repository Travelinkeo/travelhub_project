import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

logger = logging.getLogger(__name__)


@login_required
def registrar_pago_modal_view(request, venta_id):
    """registrar_pago_modal_view."""
    from apps.bookings.models import Venta
    from apps.finance.forms import RegistroPagoFastForm

    # Validamos que la venta pertenezca a la misma agencia del usuario logueado (Multi-Tenant Guard)
    venta = get_object_or_404(Venta, id_venta=venta_id, agencia=request.user.agencia)
    agencia = request.user.agencia
    is_htmx = request.headers.get("HX-Request") == "true"

    if request.method == "POST":
        # Manejo de MultipartFormData por el archivo 'comprobante'
        form = RegistroPagoFastForm(
            request.POST, request.FILES, agencia=agencia, venta_id=venta.id_venta
        )
        if form.is_valid():
            pago = form.save()

            # Si es HTMX, devolvemos un bloque de éxito directo para inyectar en el DOM
            if is_htmx:
                return render(
                    request, "finance/partials/pago_exitoso.html", {"pago": pago, "venta": venta}
                )

        # Si el formulario es inválido y es HTMX, re-renderizamos solo el fragmento del formulario con los errores
        if is_htmx:
            return render(
                request, "finance/partials/form_pago_inner.html", {"form": form, "venta": venta}
            )
    else:
        form = RegistroPagoFastForm(agencia=agencia, venta_id=venta.id_venta)

    return render(request, "finance/registro_pago_page.html", {"form": form, "venta": venta})

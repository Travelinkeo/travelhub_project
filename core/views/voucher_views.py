# core/views/voucher_views.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from apps.bookings.models import Venta
from apps.bookings.services.voucher_service import generar_voucher_unificado
from core.security import get_object_tenant_or_404


@login_required
def generar_voucher(request, venta_id):
    """
    Genera un voucher unificado en PDF para una venta específica.
    Abre el PDF en el navegador de manera inline en lugar de forzar descarga.
    """
    agencia = getattr(request, "agencia", None)
    venta = get_object_tenant_or_404(Venta, agencia, pk=venta_id)
    pdf_bytes, filename = generar_voucher_unificado(venta.pk)

    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
    else:
        return HttpResponse("No se pudo generar el voucher", status=500)

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from apps.common.services.pdf_service import (
    generar_pdf_voucher_unificado,
    generar_y_guardar_ticket_pdf,
)
from core.models import BoletoImportado, Venta


def test():
    b = BoletoImportado.objects.first()
    if b:
        print(f"Testing Boleto {b.id}")
        pdf = generar_y_guardar_ticket_pdf(b)
        print("Ticket PDF generado:", getattr(b, "boleto_pdf", "No PDF stored"))
    else:
        print("No boletos found")

    v = Venta.objects.first()
    if v:
        print(f"Testing Venta {v.id}")
        pdf = generar_pdf_voucher_unificado(v)
        if pdf:
            print("Voucher PDF generado")
    else:
        print("No ventas found")


if __name__ == "__main__":
    test()

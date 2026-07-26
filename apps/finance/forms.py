from django import forms

from .models import Pago


class RegistroPagoFastForm(forms.ModelForm):
    """RegistroPagoFastForm."""

    class Meta:
        model = Pago
        fields = [
            "factura",
            "monto_usd",
            "monto_ves",
            "metodo_pago",
            "referencia",
            "fecha_pago",
        ]
        widgets = {
            "fecha_pago": forms.DateInput(attrs={"type": "date"}),
            "monto_usd": forms.NumberInput(attrs={"step": "0.0001"}),
            "monto_ves": forms.NumberInput(attrs={"step": "0.0001"}),
        }

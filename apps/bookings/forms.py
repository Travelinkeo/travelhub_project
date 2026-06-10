from django import forms

from apps.bookings.models import BoletoImportado, FeeVenta


class FeeVentaForm(forms.ModelForm):
    class Meta:
        model = FeeVenta
        fields = ["tipo_fee", "monto", "moneda", "descripcion", "es_comision_agencia"]
        widgets = {
            "tipo_fee": forms.Select(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "monto": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full",
                }
            ),
            "moneda": forms.Select(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "descripcion": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full",
                    "placeholder": "Ej. Fee de Emisión",
                }
            ),
            "es_comision_agencia": forms.CheckboxInput(
                attrs={
                    "class": "rounded border-gray-700 text-primary focus:ring-primary bg-gray-800/50 w-5 h-5"
                }
            ),
        }


class BoletoManualForm(forms.ModelForm):
    class Meta:
        model = BoletoImportado
        fields = [
            "numero_boleto",
            "nombre_pasajero_completo",
            "ruta_vuelo",
            "fecha_emision_boleto",
            "aerolinea_emisora",
            "direccion_aerolinea",
            "agente_emisor",
            "foid_pasajero",
            "localizador_pnr",
            "tarifa_base",
            "impuestos_descripcion",
            "total_boleto",
        ]
        widgets = {
            "ruta_vuelo": forms.Textarea(attrs={"rows": 4}),
            "impuestos_descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_emision_boleto": forms.DateInput(attrs={"type": "date"}),
        }


class BoletoFileUploadForm(forms.ModelForm):
    class Meta:
        model = BoletoImportado
        fields = ["archivo_boleto"]


class BoletoAereoUpdateForm(forms.ModelForm):
    class Meta:
        model = BoletoImportado
        fields = [
            "tarifa_base",
            "impuestos_total_calculado",
            "total_boleto",
            "exchange_monto",
            "void_monto",
            "fee_servicio",
            "igtf_monto",
            "comision_agencia",
        ]
        widgets = {
            "tarifa_base": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm"}
            ),
            "impuestos_total_calculado": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm"}
            ),
            "total_boleto": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm"}
            ),
            "exchange_monto": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm"}
            ),
            "void_monto": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm text-danger"}
            ),
            "fee_servicio": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm"}
            ),
            "igtf_monto": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm"}
            ),
            "comision_agencia": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control form-control-sm"}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        tarifa = cleaned.get("tarifa_base")
        impuestos = cleaned.get("impuestos_total_calculado")
        total = cleaned.get("total_boleto")
        if tarifa is not None and impuestos is not None and total is None:
            cleaned["total_boleto"] = tarifa + impuestos
        return cleaned

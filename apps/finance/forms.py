from django import forms

from .models import CanalRecaudacion, Pago
from .models.reconciliacion import ReporteReconciliacion


class ReporteReconciliacionForm(forms.ModelForm):
    class Meta:
        model = ReporteReconciliacion
        fields = ["proveedor", "archivo"]
        widgets = {
            "proveedor": forms.Select(
                attrs={
                    "class": "w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                }
            ),
            "archivo": forms.FileInput(
                attrs={
                    "class": "w-full text-sm text-gray-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer border border-gray-700 rounded-lg bg-gray-900 focus:outline-none focus:border-indigo-500 transition-colors"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Placeholder or specific styling if needed
        self.fields["proveedor"].widget.choices = [
            ("", "Seleccione un GDS / Consolidador"),
            ("SABRE", "SABRE"),
            ("AMADEUS", "AMADEUS"),
            ("KIU", "KIU SYSTEM"),
            ("TICKET_CONSOLIDATOR", "CONSOLIDADOR GENERICO"),
        ]


class RegistroPagoFastForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = [
            "canal_recaudacion",
            "monto",
            "moneda",
            "tasa_cambio",
            "referencia",
            "fecha_pago",
            "comprobante",
            "notas",
        ]
        widgets = {
            "fecha_pago": forms.DateInput(attrs={"type": "date", "class": "form-input-premium"}),
            "notas": forms.Textarea(attrs={"rows": 2, "class": "form-input-premium"}),
            "monto": forms.NumberInput(attrs={"step": "0.01", "class": "form-input-premium"}),
            "tasa_cambio": forms.NumberInput(
                attrs={"step": "0.0001", "class": "form-input-premium"}
            ),
            "referencia": forms.TextInput(attrs={"class": "form-input-premium"}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos la agencia del contexto para el aislamiento multi-tenant
        self.agencia = kwargs.pop("agencia", None)
        self.venta_id = kwargs.pop("venta_id", None)
        super().__init__(*args, **kwargs)

        if self.agencia:
            # Regla estricta SaaS: Solo canales activos de esta agencia específica
            self.fields["canal_recaudacion"].queryset = CanalRecaudacion.objects.filter(
                agencia=self.agencia, activo=True
            )

        # Estilos rápidos para Tailwind de forma unificada si no usas selectores avanzados
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all duration-200",
                )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.agencia:
            instance.agencia = self.agencia
        if self.venta_id:
            instance.venta_id = self.venta_id
        if commit:
            instance.save()
        return instance

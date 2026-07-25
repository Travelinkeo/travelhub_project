"""Formularios Django para la aplicación cotizaciones.
"""

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.common.models import Moneda
from apps.cotizaciones.models import Cotizacion, ItemCotizacion


class CotizacionForm:
    """Formulario para cotizacion. Uso: instanciar según necesidad del dominio.
    """
    class Meta:
        model = Cotizacion
        fields = [
            "cliente",
            "nombre_cliente_manual",
            "fecha_validez",
            "moneda",
            "destino",
            "descripcion_general",
            "notas_internas",
            "condiciones_comerciales",
        ]
        widgets = {
            "fecha_validez": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent",
                }
            ),
            "destino": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent",
                    "placeholder": "Ej. Madrid, España",
                }
            ),
            "descripcion_general": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent",
                }
            ),
            "notas_internas": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent",
                }
            ),
            "condiciones_comerciales": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent",
                }
            ),
            "cliente": forms.Select(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent"
                }
            ),
            "nombre_cliente_manual": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent",
                    "placeholder": "Nombre del prospecto o empresa",
                }
            ),
            "moneda": forms.Select(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # __init__: Método de inicialización de la clase.
        super().__init__(*args, **kwargs)
        # Order currencies: Local first, then by name
        self.fields["moneda"].queryset = Moneda.objects.order_by("-es_moneda_local", "nombre")
        # Hacer cliente opcional porque puede usarse nombre manual
        self.fields["cliente"].required = False

    def clean(self):
        # clean: Limpia/valida los campos del modelo. Args: None. Returns: None.
        cleaned_data = super().clean()
        cliente = cleaned_data.get("cliente")
        nombre_manual = cleaned_data.get("nombre_cliente_manual")

        if not cliente and not nombre_manual:
            raise forms.ValidationError(
                _("Debe seleccionar un Cliente o ingresar un Nombre Manual.")
            )

        return cleaned_data


ItemCotizacionFormSet = inlineformset_factory(
    Cotizacion,
    ItemCotizacion,
    fields=[
        "producto_servicio",
        "descripcion_personalizada",
        "cantidad",
        "precio_unitario",
        "impuestos_item",
    ],
    extra=1,
    can_delete=True,
    widgets={
        "producto_servicio": forms.Select(
            attrs={
                "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-full focus:ring-2 focus:ring-primary focus:border-transparent"
            }
        ),
        "descripcion_personalizada": forms.TextInput(
            attrs={
                "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-full focus:ring-2 focus:ring-primary focus:border-transparent",
                "placeholder": "Opcional",
            }
        ),
        "cantidad": forms.NumberInput(
            attrs={
                "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-20 focus:ring-2 focus:ring-primary focus:border-transparent"
            }
        ),
        "precio_unitario": forms.NumberInput(
            attrs={
                "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-32 focus:ring-2 focus:ring-primary focus:border-transparent",
                "step": "0.01",
            }
        ),
        "impuestos_item": forms.NumberInput(
            attrs={
                "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-24 focus:ring-2 focus:ring-primary focus:border-transparent",
                "step": "0.01",
            }
        ),
    },
)

from django import forms

from apps.bookings.models import TarifaHabitacion, TipoHabitacion


class TarifaHabitacionForm(forms.ModelForm):
    """Formulario para que cada agencia administre sus tarifas por habitación y vigencia."""

    class Meta:
        model = TarifaHabitacion
        fields = [
            "tipo_habitacion",
            "nombre_temporada",
            "fecha_inicio",
            "fecha_fin",
            "moneda",
            "tipo_tarifa",
            "tarifa_sgl",
            "tarifa_dbl",
            "tarifa_tpl",
            "tarifa_cpl",
            "tarifa_nino",
        ]
        widgets = {
            "fecha_inicio": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
            "fecha_fin": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
            "nombre_temporada": forms.TextInput(
                attrs={
                    "placeholder": "Ej: Temporada Alta 2026 / Especial",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
            "tipo_habitacion": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5"
                }
            ),
            "moneda": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5"
                }
            ),
            "tipo_tarifa": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5"
                }
            ),
            "tarifa_sgl": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "placeholder": "0.00",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
            "tarifa_dbl": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "placeholder": "0.00",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
            "tarifa_tpl": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "placeholder": "0.00",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
            "tarifa_cpl": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "placeholder": "0.00",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
            "tarifa_nino": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "placeholder": "0.00",
                    "class": "w-full rounded-lg border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-primary)] p-2.5",
                }
            ),
        }

    def __init__(self, *args, hotel=None, **kwargs):
        super().__init__(*args, **kwargs)
        if hotel:
            self.fields["tipo_habitacion"].queryset = TipoHabitacion.objects.filter(hotel=hotel)

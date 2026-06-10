from django import forms

from apps.crm.models import Pasajero


class PasajeroForm(forms.ModelForm):
    # Campos virtuales para preferencias (se serializan al JSON field)
    pref_comida_veg = forms.BooleanField(required=False, label="Vegetariana (VGML)")
    pref_comida_kosher = forms.BooleanField(required=False, label="Kosher (KSML)")
    pref_comida_sin_gluten = forms.BooleanField(required=False, label="Sin Gluten (GFML)")

    pref_asiento = forms.ChoiceField(
        choices=[("", "Sin Preferencia"), ("VENTANA", "Ventana"), ("PASILLO", "Pasillo")],
        required=False,
        label="Preferencia de Asiento",
        widget=forms.Select(
            attrs={
                "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
            }
        ),
    )

    pref_asistencia_silla = forms.BooleanField(required=False, label="Silla de Ruedas (WCHR)")
    pref_notas = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full",
            }
        ),
        required=False,
        label="Notas de Preferencias",
    )

    class Meta:
        model = Pasajero
        fields = [
            "nombres",
            "apellidos",
            "cedula_identidad",
            "numero_pasaporte",
            "fecha_nacimiento",
            "email",
            "telefono",
            "nacionalidad",
            "pais_emision_documento",
            "fecha_vencimiento_pasaporte",
        ]
        widgets = {
            "fecha_nacimiento": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full",
                }
            ),
            "fecha_vencimiento_pasaporte": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full",
                }
            ),
            "nombres": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "apellidos": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "cedula_identidad": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "numero_pasaporte": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "nacionalidad": forms.Select(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
            "pais_emision_documento": forms.Select(
                attrs={
                    "class": "bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargar preferencias guardadas en JSON si editamos una instancia
        if self.instance and self.instance.pk and self.instance.preferencias:
            prefs = self.instance.preferencias
            self.fields["pref_comida_veg"].initial = prefs.get("comida_vegetariana", False)
            self.fields["pref_comida_kosher"].initial = prefs.get("comida_kosher", False)
            self.fields["pref_comida_sin_gluten"].initial = prefs.get("comida_sin_gluten", False)
            self.fields["pref_asiento"].initial = prefs.get("asiento", "")
            self.fields["pref_asistencia_silla"].initial = prefs.get("asistencia_silla", False)
            self.fields["pref_notas"].initial = prefs.get("notas", "")

    def save(self, commit=True):
        pasajero = super().save(commit=False)
        # Construir el JSON de preferencias
        pasajero.preferencias = {
            "comida_vegetariana": self.cleaned_data.get("pref_comida_veg"),
            "comida_kosher": self.cleaned_data.get("pref_comida_kosher"),
            "comida_sin_gluten": self.cleaned_data.get("pref_comida_sin_gluten"),
            "asiento": self.cleaned_data.get("pref_asiento"),
            "asistencia_silla": self.cleaned_data.get("pref_asistencia_silla"),
            "notas": self.cleaned_data.get("pref_notas"),
        }
        if commit:
            pasajero.save()
        return pasajero

from django import forms
from django.contrib.auth.models import User
from core.models.agencia import Agencia, UsuarioAgencia

class AgenciaSettingsForm(forms.ModelForm):
    """Formulario para editar la configuración de la agencia."""
    
    class Meta:
        model = Agencia
        fields = [
            'nombre_comercial', 'rif', 'iata',
            'telefono_principal', 'email_principal', 'email_ventas',
            'direccion', 'ciudad', 'estado', 'pais',
            'logo', 'color_primario', 'color_secundario',
            'moneda_principal', 'zona_horaria', 'idioma'
        ]
        widgets = {
            'color_primario': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 p-1 rounded cursor-pointer'}),
            'color_secundario': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 p-1 rounded cursor-pointer'}),
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'form-input w-full rounded-md border-gray-300'


class UsuarioAgenciaForm(forms.Form):
    """Formulario para invitar/crear un usuario de agencia."""
    
    email = forms.EmailField(label="Correo Electrónico")
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    rol = forms.ChoiceField(choices=UsuarioAgencia.ROLES, label="Rol")
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado en TravelHub.")
        return email

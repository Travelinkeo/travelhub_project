from django import forms
from django.contrib.auth.models import User
from core.models.agencia import Agencia

class UserProfileForm(forms.ModelForm):
    """Formulario para editar datos personales del usuario."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5', 'placeholder': 'Tu nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5', 'placeholder': 'Tus apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5', 'placeholder': 'nombre@ejemplo.com'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = "Nombres"
        self.fields['last_name'].label = "Apellidos"
        self.fields['email'].label = "Correo Electrónico"


class AgencyBrandingForm(forms.ModelForm):
    """Formulario para branding y contacto de la agencia."""
    class Meta:
        model = Agencia
        fields = [
            'nombre_comercial', 'rif', 'iata',
            'telefono_principal', 'email_principal',
            'direccion', 'ciudad', 'pais',
            'logo', 'color_primario'
        ]
        widgets = {
            'nombre_comercial': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'rif': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'iata': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'telefono_principal': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'email_principal': forms.EmailInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'direccion': forms.Textarea(attrs={'rows': 3, 'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'ciudad': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'pais': forms.TextInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5'}),
            'color_primario': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 bg-transparent border-0 cursor-pointer rounded'}),
            'logo': forms.FileInput(attrs={'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700'}),
        }

class AgencyAutomationForm(forms.ModelForm):
    """Formulario para configurar el Mailbot y APIs."""
    class Meta:
        model = Agencia
        fields = ['email_monitor_user', 'email_monitor_password', 'email_monitor_active']
        widgets = {
            'email_monitor_user': forms.EmailInput(attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5', 'placeholder': 'ejemplo@gmail.com'}),
            'email_monitor_password': forms.PasswordInput(render_value=True, attrs={'class': 'bg-slate-800 border border-slate-700 text-white rounded-lg block w-full p-2.5', 'placeholder': 'Contraseña de Aplicación'}),
            'email_monitor_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-600 ring-offset-gray-800'}),
        }

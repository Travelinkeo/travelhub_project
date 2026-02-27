from django import forms
from django.contrib.auth.models import User
from .models import Agencia, UsuarioAgencia

class AgenciaForm(forms.ModelForm):
    class Meta:
        model = Agencia
        fields = [
            'nombre', 'nombre_comercial', 'rif', 'iata',
            'telefono_principal', 'telefono_secundario', 'email_principal', 'email_soporte', 'email_ventas',
            'direccion', 'ciudad', 'estado', 'pais', 'codigo_postal',
            'logo', 'color_primario', 'color_secundario',
            'website', 'facebook', 'instagram', 'twitter', 'whatsapp',
            'moneda_principal', 'zona_horaria', 'idioma'
        ]
        widgets = {
            'color_primario': forms.TextInput(attrs={'type': 'color'}),
            'color_secundario': forms.TextInput(attrs={'type': 'color'}),
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }

class UsuarioAgenciaForm(forms.ModelForm):
    username = forms.CharField(label="Nombre de Usuario")
    email = forms.EmailField(label="Email")
    first_name = forms.CharField(label="Nombre", required=False)
    last_name = forms.CharField(label="Apellido", required=False)
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña", required=False, help_text="Dejar en blanco para no cambiar")

    class Meta:
        model = UsuarioAgencia
        fields = ['rol', 'activo']

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)
        if self.user_instance:
            self.fields['username'].initial = self.user_instance.username
            self.fields['email'].initial = self.user_instance.email
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            self.fields['username'].disabled = True # No permitir cambiar username fácilmente

    def save(self, commit=True):
        usuario_agencia = super().save(commit=False)
        
        # Logic to create or update User
        if self.user_instance:
            user = self.user_instance
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            if self.cleaned_data.get('password'):
                user.set_password(self.cleaned_data['password'])
            user.save()
        else:
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name']
            )
            usuario_agencia.usuario = user
        
        if commit:
            usuario_agencia.save()
        return usuario_agencia

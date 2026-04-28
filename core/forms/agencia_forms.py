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
            'logo', 'logo_light', 'logo_dark', 'logo_pdf_base64', 'logo_pdf_dark_base64',
            'eslogan', 'pie_pagina', 'terminos_condiciones',
            'ui_theme', 'color_primario', 'color_secundario',
            'color_amadeus', 'color_kiu', 'color_copa',
            'color_tk_connect', 'color_wingo', 'color_travelport',
            'plantilla_boletos', 'plantilla_vouchers', 'plantilla_facturas',
            'moneda_principal', 'zona_horaria', 'idioma'
        ]
        widgets = {
            'color_primario': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'color_secundario': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'color_amadeus': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'color_kiu': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'color_copa': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'color_tk_connect': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'color_wingo': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'color_travelport': forms.TextInput(attrs={'type': 'color', 'class': 'size-10 rounded-lg p-0 border-none cursor-pointer'}),
            'direccion': forms.Textarea(attrs={'rows': 3, 'class': 'input-base h-auto py-2'}),
            'ui_theme': forms.Select(attrs={'class': 'input-base bg-surface-2'}),
            'logo_pdf_base64': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'w-full bg-slate-50 dark:bg-[#0e1f18] border border-slate-200 dark:border-[#234836] rounded-lg p-4 text-xs font-mono text-slate-600 dark:text-[#92c9ad] resize-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-slate-400 dark:placeholder:text-[#32674d]',
                'placeholder': 'data:image/png;base64,...'
            }),
            'logo_pdf_dark_base64': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'w-full bg-slate-50 dark:bg-[#0e1f18] border border-slate-200 dark:border-[#234836] rounded-lg p-4 text-xs font-mono text-slate-600 dark:text-[#92c9ad] resize-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-slate-400 dark:placeholder:text-[#32674d]',
                'placeholder': 'data:image/png;base64,...'
            }),
        }

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'input-base'


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

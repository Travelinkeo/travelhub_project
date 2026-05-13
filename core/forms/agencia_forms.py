from django import forms
from django.contrib.auth.models import User

from core.models.agencia import Agencia, AgenciaBranding, AgenciaConfiguracion, UsuarioAgencia


class AgenciaSettingsForm(forms.ModelForm):
    """Formulario para editar la configuración de la agencia."""
    
    # Campos de Branding
    logo = forms.ImageField(required=False)
    logo_light = forms.ImageField(required=False)
    logo_dark = forms.ImageField(required=False)
    logo_pdf_base64 = forms.CharField(widget=forms.Textarea, required=False)
    logo_pdf_dark_base64 = forms.CharField(widget=forms.Textarea, required=False)
    eslogan = forms.CharField(required=False)
    pie_pagina = forms.CharField(widget=forms.Textarea, required=False)
    terminos_condiciones = forms.CharField(widget=forms.Textarea, required=False)
    ui_theme = forms.ChoiceField(choices=Agencia.THEME_CHOICES, required=False)
    color_primario = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    color_secundario = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    color_amadeus = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    color_kiu = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    color_copa = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    color_tk_connect = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    color_wingo = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    color_travelport = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    plantilla_boletos = forms.CharField(required=False)
    plantilla_vouchers = forms.CharField(required=False)
    plantilla_facturas = forms.CharField(required=False)
    
    # Campos de Configuración
    moneda_principal = forms.CharField(max_length=3, required=False)
    zona_horaria = forms.CharField(max_length=50, required=False)
    idioma = forms.CharField(max_length=5, required=False)

    class Meta:
        model = Agencia
        fields = [
            'nombre_comercial', 'rif', 'iata',
            'telefono_principal', 'email_principal', 'email_ventas',
            'direccion', 'ciudad', 'estado', 'pais'
        ]
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 3, 'class': 'input-base h-auto py-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Cargar valores iniciales de los componentes si existen
        if self.instance and self.instance.pk:
            if hasattr(self.instance, 'branding') and self.instance.branding:
                b = self.instance.branding
                branding_fields = [
                    'logo', 'logo_light', 'logo_dark', 'logo_pdf_base64', 'logo_pdf_dark_base64',
                    'eslogan', 'pie_pagina', 'terminos_condiciones', 'ui_theme', 'color_primario',
                    'color_secundario', 'color_amadeus', 'color_kiu', 'color_copa',
                    'color_tk_connect', 'color_wingo', 'color_travelport',
                    'plantilla_boletos', 'plantilla_vouchers', 'plantilla_facturas'
                ]
                for field in branding_fields:
                    if field in self.fields:
                        self.fields[field].initial = getattr(b, field)
            
            if hasattr(self.instance, 'configuracion') and self.instance.configuracion:
                c = self.instance.configuracion
                config_fields = ['moneda_principal', 'zona_horaria', 'idioma']
                for field in config_fields:
                    if field in self.fields:
                        self.fields[field].initial = getattr(c, field)

        # Aplicar clases CSS
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'input-base'
            
            # Estilos especiales para colores
            if field_name.startswith('color_'):
                field.widget.attrs['class'] = 'size-10 rounded-lg p-0 border-none cursor-pointer'

    def save(self, commit=True):
        agencia = super().save(commit=False)
        if commit:
            agencia.save()
            
            # Guardar Branding
            branding, _ = AgenciaBranding.objects.get_or_create(agencia=agencia)
            branding_fields = [
                'logo', 'logo_light', 'logo_dark', 'logo_pdf_base64', 'logo_pdf_dark_base64',
                'eslogan', 'pie_pagina', 'terminos_condiciones', 'ui_theme', 'color_primario',
                'color_secundario', 'color_amadeus', 'color_kiu', 'color_copa',
                'color_tk_connect', 'color_wingo', 'color_travelport',
                'plantilla_boletos', 'plantilla_vouchers', 'plantilla_facturas'
            ]
            for field in branding_fields:
                if field in self.cleaned_data:
                    setattr(branding, field, self.cleaned_data[field])
            branding.save()
            
            # Guardar Configuración
            config, _ = AgenciaConfiguracion.objects.get_or_create(agencia=agencia)
            config_fields = ['moneda_principal', 'zona_horaria', 'idioma']
            for field in config_fields:
                if field in self.cleaned_data:
                    setattr(config, field, self.cleaned_data[field])
            config.save()
            
        return agencia


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

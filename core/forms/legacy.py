# Archivo: core/forms.py
from django import forms

from apps.bookings.models import BoletoImportado, FeeVenta

class FeeVentaForm(forms.ModelForm):
    class Meta:
        model = FeeVenta
        fields = ['tipo_fee', 'monto', 'moneda', 'descripcion', 'es_comision_agencia']
        widgets = {
            'tipo_fee': forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'monto': forms.NumberInput(attrs={'step': '0.01', 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'moneda': forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'descripcion': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full', 'placeholder': 'Ej. Fee de Emisión'}),
            'es_comision_agencia': forms.CheckboxInput(attrs={'class': 'rounded border-gray-700 text-primary focus:ring-primary bg-gray-800/50 w-5 h-5'}),
        }



class BoletoManualForm(forms.ModelForm):
    class Meta:
        model = BoletoImportado
        fields = [
            'numero_boleto',
            'nombre_pasajero_completo',
            'ruta_vuelo',
            'fecha_emision_boleto',
            'aerolinea_emisora',
            'direccion_aerolinea',
            'agente_emisor',
            'foid_pasajero',
            'localizador_pnr',
            'tarifa_base',
            'impuestos_descripcion',
            'total_boleto',
        ]
        widgets = {
            'ruta_vuelo': forms.Textarea(attrs={'rows': 4}),
            'impuestos_descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_emision_boleto': forms.DateInput(attrs={'type': 'date'}),
        }

class BoletoFileUploadForm(forms.ModelForm):
    class Meta:
        model = BoletoImportado
        fields = ['archivo_boleto']


class BoletoAereoUpdateForm(forms.ModelForm):
    class Meta:
        model = BoletoImportado
        fields = [
            'tarifa_base', 'impuestos_total_calculado', 'total_boleto',
            'exchange_monto', 'void_monto', 'fee_servicio', 'igtf_monto', 'comision_agencia'
        ]
        widgets = {
            'tarifa_base': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm'}),
            'impuestos_total_calculado': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm'}),
            'total_boleto': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm'}),
            'exchange_monto': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm'}),
            'void_monto': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm text-danger'}),
            'fee_servicio': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm'}),
            'igtf_monto': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm'}),
            'comision_agencia': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control form-control-sm'}),
        }

    def clean(self):
        cleaned = super().clean()
        # Opcional: recalcular total si usuario deja total vacío pero provee tarifa + impuestos
        tarifa = cleaned.get('tarifa_base')
        impuestos = cleaned.get('impuestos_total_calculado')
        total = cleaned.get('total_boleto')
        if tarifa is not None and impuestos is not None and total is None:
            cleaned['total_boleto'] = tarifa + impuestos
        return cleaned


from django.forms import inlineformset_factory
from apps.cotizaciones.models import Cotizacion, ItemCotizacion

class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['cliente', 'nombre_cliente_manual', 'fecha_validez', 'moneda', 'destino', 'descripcion_general', 'notas_internas', 'condiciones_comerciales']
        widgets = {
            'fecha_validez': forms.DateInput(attrs={'type': 'date', 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent'}),
            'destino': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent', 'placeholder': 'Ej. Madrid, España'}),
            'descripcion_general': forms.Textarea(attrs={'rows': 3, 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent'}),
            'notas_internas': forms.Textarea(attrs={'rows': 2, 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent'}),
            'condiciones_comerciales': forms.Textarea(attrs={'rows': 3, 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent'}),
            'cliente': forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent'}),
            'nombre_cliente_manual': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent', 'placeholder': 'Nombre del prospecto o empresa'}),
            'moneda': forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full focus:ring-2 focus:ring-primary focus:border-transparent'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models_catalogos import Moneda
        # Order currencies: Local first, then by name
        self.fields['moneda'].queryset = Moneda.objects.order_by('-es_moneda_local', 'nombre')
        # Hacer cliente opcional porque puede usarse nombre manual
        self.fields['cliente'].required = False

    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get('cliente')
        nombre_manual = cleaned_data.get('nombre_cliente_manual')

        if not cliente and not nombre_manual:
            raise forms.ValidationError(_("Debe seleccionar un Cliente o ingresar un Nombre Manual."))
        
        return cleaned_data

ItemCotizacionFormSet = inlineformset_factory(
    Cotizacion, ItemCotizacion,
    fields=['producto_servicio', 'descripcion_personalizada', 'cantidad', 'precio_unitario', 'impuestos_item'],
    extra=1,
    can_delete=True,
    widgets={
        'producto_servicio': forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-full focus:ring-2 focus:ring-primary focus:border-transparent'}),
        'descripcion_personalizada': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-full focus:ring-2 focus:ring-primary focus:border-transparent', 'placeholder': 'Opcional'}),
        'cantidad': forms.NumberInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-20 focus:ring-2 focus:ring-primary focus:border-transparent'}),
        'precio_unitario': forms.NumberInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-32 focus:ring-2 focus:ring-primary focus:border-transparent', 'step': '0.01'}),
        'impuestos_item': forms.NumberInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-3 py-1 w-24 focus:ring-2 focus:ring-primary focus:border-transparent', 'step': '0.01'}),
    }
)

from apps.crm.models import Pasajero

class PasajeroForm(forms.ModelForm):
    # Campos virtuales para preferencias (se serializan al JSON field)
    pref_comida_veg = forms.BooleanField(required=False, label="Vegetariana (VGML)")
    pref_comida_kosher = forms.BooleanField(required=False, label="Kosher (KSML)")
    pref_comida_sin_gluten = forms.BooleanField(required=False, label="Sin Gluten (GFML)")
    
    pref_asiento = forms.ChoiceField(
        choices=[('', 'Sin Preferencia'), ('VENTANA', 'Ventana'), ('PASILLO', 'Pasillo')],
        required=False,
        label="Preferencia de Asiento",
        widget=forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'})
    )
    
    pref_asistencia_silla = forms.BooleanField(required=False, label="Silla de Ruedas (WCHR)")
    pref_notas = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
        required=False, 
        label="Notas de Preferencias"
    )

    class Meta:
        model = Pasajero
        fields = [
            'nombres', 'apellidos', 'cedula_identidad', 'numero_pasaporte',
            'fecha_nacimiento', 'email', 'telefono', 'nacionalidad', 
            'pais_emision_documento', 'fecha_vencimiento_documento', 'preferencias'
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'apellidos': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'cedula_identidad': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'numero_pasaporte': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'email': forms.EmailInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'telefono': forms.TextInput(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'fecha_vencimiento_documento': forms.DateInput(attrs={'type': 'date', 'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'preferencias': forms.HiddenInput(), # Se llena automáticamente
            'nacionalidad': forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
            'pais_emision_documento': forms.Select(attrs={'class': 'bg-gray-800/50 border border-gray-700 text-white rounded-xl px-4 py-2 w-full'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargar valores iniciales desde el JSON field si existe
        if self.instance and self.instance.preferencias:
            prefs = self.instance.preferencias
            self.fields['pref_comida_veg'].initial = 'VGML' in prefs.get('comida', [])
            self.fields['pref_comida_kosher'].initial = 'KSML' in prefs.get('comida', [])
            self.fields['pref_comida_sin_gluten'].initial = 'GFML' in prefs.get('comida', [])
            self.fields['pref_asiento'].initial = prefs.get('asiento', '')
            self.fields['pref_asistencia_silla'].initial = 'WCHR' in prefs.get('asistencia', [])
            self.fields['pref_notas'].initial = prefs.get('notas', '')

    def clean(self):
        cleaned_data = super().clean()
        # Construir el JSON
        preferencias = {
            'comida': [],
            'asiento': cleaned_data.get('pref_asiento'),
            'asistencia': [],
            'notas': cleaned_data.get('pref_notas')
        }
        
        if cleaned_data.get('pref_comida_veg'): preferencias['comida'].append('VGML')
        if cleaned_data.get('pref_comida_kosher'): preferencias['comida'].append('KSML')
        if cleaned_data.get('pref_comida_sin_gluten'): preferencias['comida'].append('GFML')
        
        if cleaned_data.get('pref_asistencia_silla'): preferencias['asistencia'].append('WCHR')
        
        cleaned_data['preferencias'] = preferencias
        return cleaned_data
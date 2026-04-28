from django import forms
from .models.reconciliacion import ReporteReconciliacion

class ReporteReconciliacionForm(forms.ModelForm):
    class Meta:
        model = ReporteReconciliacion
        fields = ['proveedor', 'archivo']
        widgets = {
            'proveedor': forms.Select(attrs={
                'class': 'w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors'
            }),
            'archivo': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer border border-gray-700 rounded-lg bg-gray-900 focus:outline-none focus:border-indigo-500 transition-colors'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Placeholder or specific styling if needed
        self.fields['proveedor'].widget.choices = [
            ('', 'Seleccione un GDS / Consolidador'),
            ('SABRE', 'SABRE'),
            ('AMADEUS', 'AMADEUS'),
            ('KIU', 'KIU SYSTEM'),
            ('TICKET_CONSOLIDATOR', 'CONSOLIDADOR GENERICO')
        ]

from django import forms
from .models import Articulo, GuiaDestino

class ArticuloForm(forms.ModelForm):
    class Meta:
        model = Articulo
        fields = ['titulo', 'slug', 'resumen', 'contenido', 'destino', 'estado', 'meta_titulo', 'meta_descripcion']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'slug': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'resumen': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white', 'rows': 3}),
            'contenido': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white', 'rows': 10}),
            'destino': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'estado': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'meta_titulo': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'meta_descripcion': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white', 'rows': 2}),
        }

class GuiaDestinoForm(forms.ModelForm):
    class Meta:
        model = GuiaDestino
        fields = ['nombre', 'descripcion', 'mejor_epoca', 'requisitos_visa', 'idioma', 'moneda_local', 'imagen_url']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white', 'rows': 5}),
            'mejor_epoca': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'requisitos_visa': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white', 'rows': 3}),
            'idioma': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'moneda_local': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
            'imagen_url': forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white'}),
        }

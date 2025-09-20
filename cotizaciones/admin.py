from django.contrib import admin
from .models import Cotizacion, ItemCotizacion

class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 1
    autocomplete_fields = ['producto_servicio']

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('numero_cotizacion', 'cliente', 'fecha_emision', 'total_cotizado', 'moneda', 'estado')
    search_fields = ('numero_cotizacion', 'cliente__nombres', 'cliente__apellidos')
    list_filter = ('estado', 'fecha_emision')
    autocomplete_fields = ['cliente', 'moneda']
    inlines = [ItemCotizacionInline]
    readonly_fields = ('total_cotizado',)

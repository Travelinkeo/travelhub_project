from django.contrib import admin
from core.models.wiki import WikiArticulo

@admin.register(WikiArticulo)
class WikiArticuloAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'categoria', 'activo', 'fecha_actualizacion']
    list_filter = ['categoria', 'activo']
    search_fields = ['titulo', 'contenido', 'tags']
    prepopulated_fields = {'slug': ('titulo',)}
    
    fieldsets = [
        ('Contenido', {
            'fields': ['titulo', 'slug', 'contenido', 'categoria', 'activo']
        }),
        ('Activadores (Contexto)', {
            'fields': ['tags'],
            'description': 'Escriba las palabras clave que activarán este mensaje. Formato lista JSON (ej: ["LASER", "EQUIPAJE"]) o Texto simple.'
        })
    ]

from django.contrib import admin
from .models import Articulo, GuiaDestino, PostRedesSociales

@admin.register(Articulo)
class ArticuloAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'destino', 'estado', 'fecha_creacion', 'generado_por_ia')
    list_filter = ('estado', 'generado_por_ia', 'destino')
    search_fields = ('titulo', 'contenido', 'destino')
    prepopulated_fields = {'slug': ('titulo',)}

@admin.register(GuiaDestino)
class GuiaDestinoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'mejor_epoca', 'idioma')
    search_fields = ('nombre', 'descripcion')

@admin.register(PostRedesSociales)
class PostRedesSocialesAdmin(admin.ModelAdmin):
    list_display = ('plataforma', 'articulo', 'publicado', 'fecha_programada')
    list_filter = ('plataforma', 'publicado')

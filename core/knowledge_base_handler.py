# Archivo: core/knowledge_base_handler.py

import logging

from django.utils import timezone
from django.utils.text import slugify

from .models.cms import ArticuloBlog, PaginaCMS

logger = logging.getLogger(__name__)

def crear_articulo_desde_gemini(datos_gemini: dict, categoria: str = "General", fuente: str = "Email procesado por IA") -> ArticuloBlog | None:
    """
    Crea y guarda un nuevo artículo en la base de conocimiento a partir del JSON extraído por Gemini.

    Args:
        datos_gemini (dict): Un diccionario con los datos extraídos por Gemini.
                             Se esperan las claves: 'titulo', 'resumen', 'puntos_clave'.
        categoria (str): La categoría para asignar al artículo en la base de conocimiento.
        fuente (str): La fuente de la información (ej: 'Email de Avianca').

    Returns:
        ArticuloBlog | None: La instancia del artículo creado y guardado, o None si ocurre un error.
    """
    try:
        titulo = datos_gemini.get('titulo')
        resumen = datos_gemini.get('resumen')
        puntos_clave = datos_gemini.get('puntos_clave')

        if not titulo or not resumen:
            logger.error("Error al crear artículo: El JSON de Gemini no contiene 'titulo' o 'resumen'.")
            return None

        # Formatear los puntos clave como una lista HTML para el contenido principal
        contenido_html = f"<h3>Resumen</h3><p>{resumen}</p>"
        if isinstance(puntos_clave, list) and puntos_clave:
            contenido_html += "<h3>Puntos Clave</h3><ul>"
            for punto in puntos_clave:
                contenido_html += f"<li>{punto}</li>"
            contenido_html += "</ul>"
        
        # Crear la instancia del artículo
        nuevo_articulo = ArticuloBlog(
            titulo=titulo,
            extracto=resumen,
            contenido=contenido_html,
            estado=PaginaCMS.EstadoPublicacion.BORRADOR,  # Se guarda como borrador para revisión
            fuente=fuente,
            categoria_conocimiento=categoria,
            fecha_publicacion=timezone.now() # Asignamos fecha de publicación para ordenamiento
        )

        # Generar slug único
        slug_base = slugify(titulo)
        slug = slug_base
        counter = 1
        while ArticuloBlog.objects.filter(slug=slug).exists():
            slug = f"{slug_base}-{counter}"
            counter += 1
        nuevo_articulo.slug = slug

        nuevo_articulo.full_clean()  # Validar el modelo
        nuevo_articulo.save()

        logger.info(f"Nuevo artículo de conocimiento creado con éxito: '{titulo}' (ID: {nuevo_articulo.id_articulo})")
        return nuevo_articulo

    except Exception as e:
        logger.error(f"Error inesperado al guardar el artículo desde Gemini: {e}")
        return None

# Ejemplo de cómo se usaría esta función desde otra parte del código (ej: un management command o una vista)
"""
def procesar_email_clasificado_como_general(contenido_json):
    # Suponiendo que 'contenido_json' es el diccionario que devuelve Gemini
    # ej: {'titulo': 'Nuevas políticas de equipaje', 'resumen': '...', 'puntos_clave': ['...']}
    
    # La fuente podría ser más específica si la tenemos, ej: el 'From' del email
    fuente_email = "Email de marketing de Iberia" 
    categoria_email = "Políticas de Aerolíneas"

    articulo_creado = crear_articulo_desde_gemini(
        datos_gemini=contenido_json,
        categoria=categoria_email,
        fuente=fuente_email
    )

    if articulo_creado:
        print(f"Artículo '{articulo_creado.titulo}' guardado en la base de conocimiento.")
    else:
        print("No se pudo guardar el artículo.")

"""
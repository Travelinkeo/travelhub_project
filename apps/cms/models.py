from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class Articulo(models.Model):
    class EstadoArticulo(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        PUBLICADO = 'PUB', _('Publicado')
        ARCHIVADO = 'ARC', _('Archivado')

    titulo = models.CharField(_("Título"), max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    resumen = models.TextField(_("Resumen"), blank=True, null=True)
    contenido = models.TextField(_("Contenido (Markdown)"))
    destino = models.CharField(_("Destino Relacionado"), max_length=100, blank=True)
    
    # Metadatos IA
    generado_por_ia = models.BooleanField(default=False)
    prompt_ia = models.TextField(blank=True, null=True)
    
    # SEO
    meta_titulo = models.CharField(max_length=255, blank=True)
    meta_descripcion = models.TextField(blank=True)
    
    estado = models.CharField(max_length=3, choices=EstadoArticulo.choices, default=EstadoArticulo.BORRADOR)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_publicacion = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = _("Artículo")
        verbose_name_plural = _("Artículos")
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo

class GuiaDestino(models.Model):
    nombre = models.CharField(_("Nombre del Destino"), max_length=100)
    descripcion = models.TextField(_("Descripción General"))
    mejor_epoca = models.CharField(_("Mejor época para viajar"), max_length=255, blank=True)
    requisitos_visa = models.TextField(_("Requisitos de Visa"), blank=True)
    idioma = models.CharField(max_length=50, default="Español")
    moneda_local = models.CharField(max_length=50, blank=True)
    
    # Imagen destacada
    imagen_url = models.URLField(blank=True, null=True)
    
    class Meta:
        verbose_name = _("Guía de Destino")
        verbose_name_plural = _("Guías de Destino")

    def __str__(self):
        return self.nombre

class PostRedesSociales(models.Model):
    class Plataforma(models.TextChoices):
        INSTAGRAM = 'INS', 'Instagram'
        FACEBOOK = 'FAC', 'Facebook'
        TELEGRAM = 'TEL', 'Telegram'
        LINKEDIN = 'LIN', 'LinkedIn'
        TWITTER = 'TWI', 'Twitter/X'

    articulo = models.ForeignKey(Articulo, related_name='posts_redes', on_delete=models.CASCADE, null=True, blank=True)
    plataforma = models.CharField(max_length=3, choices=Plataforma.choices)
    contenido = models.TextField(_("Contenido del Post (Caption)"))
    hashtags = models.CharField(max_length=255, blank=True)
    fecha_programada = models.DateTimeField(blank=True, null=True)
    publicado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _("Post en Red Social")
        verbose_name_plural = _("Posts en Redes Sociales")

    def __str__(self):
        return f"{self.get_plataforma_display()} - {self.articulo.titulo if self.articulo else 'Promo'}"

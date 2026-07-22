from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin


class Articulo(AgenciaMixin, models.Model):
    class EstadoArticulo(models.TextChoices):
        BORRADOR = "BOR", _("Borrador")
        PUBLICADO = "PUB", _("Publicado")
        ARCHIVADO = "ARC", _("Archivado")

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

    estado = models.CharField(
        max_length=3, choices=EstadoArticulo.choices, default=EstadoArticulo.BORRADOR
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_publicacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _("Artículo")
        verbose_name_plural = _("Artículos")
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.titulo


class GuiaDestino(AgenciaMixin, models.Model):
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


class PostRedesSociales(AgenciaMixin, models.Model):
    class Plataforma(models.TextChoices):
        INSTAGRAM = "INS", "Instagram"
        FACEBOOK = "FAC", "Facebook"
        TELEGRAM = "TEL", "Telegram"
        LINKEDIN = "LIN", "LinkedIn"
        TWITTER = "TWI", "Twitter/X"

    articulo = models.ForeignKey(
        Articulo, related_name="posts_redes", on_delete=models.CASCADE, null=True, blank=True
    )
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


class KBCategory(AgenciaMixin, models.Model):
    name = models.CharField(_("Nombre"), max_length=100)
    slug = models.SlugField(max_length=120)
    description = models.TextField(_("Descripción"), blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Material Symbols icon name")
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = _("Categoría KB")
        verbose_name_plural = _("Categorías KB")
        ordering = ["sort_order", "name"]
        unique_together = [("agencia", "slug")]

    def __str__(self):
        return self.name


class KBArticle(AgenciaMixin, models.Model):
    title = models.CharField(_("Título"), max_length=255)
    slug = models.SlugField(max_length=280)
    content = models.TextField(_("Contenido (Markdown)"))
    category = models.ForeignKey(
        KBCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated")

    is_public = models.BooleanField(_("Público"), default=False)
    is_published = models.BooleanField(_("Publicado"), default=False)

    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    view_count = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("Artículo KB")
        verbose_name_plural = _("Artículos KB")
        ordering = ["-is_published", "-published_at"]
        unique_together = [("agencia", "slug")]
        indexes = [
            models.Index(fields=["is_public", "is_published"]),
        ]

    def __str__(self):
        return self.title

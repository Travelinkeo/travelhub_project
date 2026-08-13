from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin


class Articulo(AgenciaMixin, models.Model):
    """Articulo."""

    class EstadoArticulo(models.TextChoices):
        """EstadoArticulo."""

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
        """__str__."""
        return self.titulo


class GuiaDestino(AgenciaMixin, models.Model):
    """GuiaDestino."""

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
        """__str__."""
        return self.nombre


class PostRedesSociales(AgenciaMixin, models.Model):
    """PostRedesSociales."""

    class Plataforma(models.TextChoices):
        """Plataforma."""

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
        """__str__."""
        return f"{self.get_plataforma_display()} - {self.articulo.titulo if self.articulo else 'Promo'}"


class KBCategory(AgenciaMixin, models.Model):
    """KBCategory."""

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
        """__str__."""
        return self.name


class KBArticle(AgenciaMixin, models.Model):
    """KBArticle."""

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
        """__str__."""
        return self.title


class KBDocument(AgenciaMixin, models.Model):
    """
    Documentos y Manuales PDF (Sabre, Amadeus, KIU, etc.) de la Base de Conocimientos.
    """

    GDS_CHOICES = [
        ("SABRE", "Sabre GDS"),
        ("AMADEUS", "Amadeus GDS"),
        ("KIU", "KIU System"),
        ("TRAVELPORT", "Travelport / Galileo"),
        ("GENERAL", "General / Operaciones"),
    ]

    title = models.CharField(_("Título del Documento"), max_length=255)
    gds_type = models.CharField(
        _("Tipo / GDS"), max_length=30, choices=GDS_CHOICES, default="GENERAL"
    )
    archivo_pdf = models.FileField(_("Archivo PDF"), upload_to="kb_documents/")
    descripcion = models.TextField(_("Descripción / Notas"), blank=True)
    is_indexed = models.BooleanField(_("Indexado en Vector RAG"), default=False)
    indexed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Documento KB / Manual")
        verbose_name_plural = _("Documentos KB / Manuales")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_gds_type_display()})"


class KnowledgeChunk(AgenciaMixin, models.Model):
    """
    Fragmentos de conocimiento vectorizados (RAG) procedentes de Wikis, Manuales PDF o Correos.
    """

    SOURCE_CHOICES = [
        ("WIKI", "Artículo de Wiki / KB"),
        ("MANUAL_GDS", "Manual PDF / GDS"),
        ("MAILBOT", "Correo Informativo / Mailbot"),
    ]

    source_type = models.CharField(_("Tipo de Fuente"), max_length=30, choices=SOURCE_CHOICES)
    source_title = models.CharField(_("Título de Fuente"), max_length=255)
    source_reference_id = models.CharField(_("Referencia ID / Archivo"), max_length=255, blank=True)
    content_chunk = models.TextField(_("Fragmento de Texto"))
    embedding_vector = models.JSONField(_("Vector Embedding"), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Fragmento Vectorial RAG")
        verbose_name_plural = _("Fragmentos Vectoriales RAG")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source_type"]),
        ]

    def __str__(self):
        return f"[{self.source_type}] {self.source_title[:40]}"


class KBHistoricalEmailLog(AgenciaMixin, models.Model):
    """
    Registro de seguimiento para la ingesta incremental de correos históricos (ej. travelinkeo@gmail.com).
    Evita reprocesar correos y duplicar vectores en RAG.
    """

    STATUS_CHOICES = [
        ("PROCESSED", "Procesado e Indexado"),
        ("SKIPPED_NOISE", "Omitido (Ruido / Transaccional)"),
        ("ERROR", "Error de Procesamiento"),
    ]

    message_id = models.CharField(_("Message-ID / UID"), max_length=255, db_index=True)
    source_email = models.CharField(
        _("Cuenta de Origen"), max_length=255, default="travelinkeo@gmail.com"
    )
    subject = models.CharField(_("Asunto"), max_length=500, blank=True)
    sender = models.CharField(_("Remitente"), max_length=255, blank=True)
    date_sent = models.DateTimeField(_("Fecha del Correo"), null=True, blank=True)
    chunks_created = models.PositiveIntegerField(_("Chunks Creados"), default=0)
    status = models.CharField(
        _("Estado"), max_length=30, choices=STATUS_CHOICES, default="PROCESSED"
    )
    error_message = models.TextField(_("Mensaje de Error"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Registro de Correo Histórico RAG")
        verbose_name_plural = _("Registros de Correos Históricos RAG")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject[:50]} ({self.get_status_display()})"

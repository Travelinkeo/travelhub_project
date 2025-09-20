# Archivo: core/models/cms.py
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models_catalogos import Moneda, Pais

from ..validators import validar_no_vacio_o_espacios


class PaginaCMS(models.Model):
    id_pagina_cms = models.AutoField(primary_key=True, verbose_name=_("ID Página CMS"))
    titulo = models.CharField(_("Título de la Página"), max_length=200, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug (URL amigable)"), max_length=255, unique=True, help_text=_("Se genera automáticamente si se deja vacío, o se puede especificar."))
    contenido = models.TextField(_("Contenido HTML/Markdown"), blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class EstadoPublicacion(models.TextChoices):
        PUBLICADO = 'PUB', _('Publicado')
        BORRADOR = 'BOR', _('Borrador')
        ARCHIVADO = 'ARC', _('Archivado')
    
    estado = models.CharField(_("Estado de Publicación"), max_length=3, choices=EstadoPublicacion.choices, default=EstadoPublicacion.BORRADOR)
    plantilla = models.CharField(_("Plantilla Django a usar"), max_length=100, blank=True, null=True, help_text=_("Ej: 'cms/pagina_detalle.html'. Si está vacío, usa una por defecto."))
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)

    class Meta:
        verbose_name = _("Página CMS")
        verbose_name_plural = _("Páginas CMS")
        ordering = ['titulo']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
            original_slug = self.slug
            counter = 1
            while PaginaCMS.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class DestinoCMS(models.Model):
    id_destino_cms = models.AutoField(primary_key=True, verbose_name=_("ID Destino CMS"))
    nombre = models.CharField(_("Nombre del Destino"), max_length=150, unique=True, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug"), max_length=170, unique=True)
    pais_ubicacion = models.ForeignKey(Pais, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("País de Ubicación"))
    descripcion_corta = models.TextField(_("Descripción Corta"), blank=True)
    descripcion_larga = models.TextField(_("Descripción Larga/Detallada"), blank=True)
    imagen_destacada = models.ImageField(_("Imagen Destacada"), upload_to='cms/destinos/', blank=True, null=True)
    mejor_epoca_viajar = models.CharField(_("Mejor Época para Viajar"), max_length=255, blank=True)
    atracciones_principales = models.TextField(_("Atracciones Principales (lista)"), blank=True, help_text=_("Separar por comas o un punto por línea."))
    estado = models.CharField(_("Estado"), max_length=3, choices=PaginaCMS.EstadoPublicacion.choices, default=PaginaCMS.EstadoPublicacion.BORRADOR)
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)

    class Meta:
        verbose_name = _("Destino CMS")
        verbose_name_plural = _("Destinos CMS")
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

class PaqueteTuristicoCMS(models.Model):
    id_paquete_cms = models.AutoField(primary_key=True, verbose_name=_("ID Paquete CMS"))
    titulo = models.CharField(_("Título del Paquete"), max_length=255, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    destino_principal = models.ForeignKey(DestinoCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Destino Principal"))
    descripcion_corta = models.TextField(_("Descripción Corta"), blank=True)
    itinerario_detallado = models.TextField(_("Itinerario Detallado"), blank=True)
    duracion_dias = models.PositiveSmallIntegerField(_("Duración (días)"), null=True, blank=True)
    precio_desde_texto = models.CharField(_("Precio Desde (texto)"), max_length=100, blank=True, help_text=_("Ej: $1,200 p/p base doble"))
    precio_numerico = models.DecimalField(_("Precio Numérico (para filtros)"), max_digits=10, decimal_places=2, null=True, blank=True)
    moneda_paquete = models.ForeignKey(Moneda, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Moneda del Paquete"))
    incluye = models.TextField(_("Qué Incluye el Paquete"), blank=True)
    no_incluye = models.TextField(_("Qué NO Incluye el Paquete"), blank=True)
    imagen_destacada = models.ImageField(_("Imagen Destacada"), upload_to='cms/paquetes/', blank=True, null=True)
    fecha_validez_inicio = models.DateField(_("Válido Desde"), null=True, blank=True)
    fecha_validez_fin = models.DateField(_("Válido Hasta"), null=True, blank=True)
    
    class EstadoPaquete(models.TextChoices):
        ACTIVO = 'ACT', _('Activo')
        INACTIVO = 'INA', _('Inactivo')
        AGOTADO = 'AGO', _('Agotado')
        BORRADOR = 'BOR', _('Borrador')
    
    estado = models.CharField(_("Estado del Paquete"), max_length=3, choices=EstadoPaquete.choices, default=EstadoPaquete.BORRADOR)
    es_destacado = models.BooleanField(_("Paquete Destacado"), default=False, help_text=_("Mostrar en la página principal o secciones destacadas."))
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)

    class Meta:
        verbose_name = _("Paquete Turístico CMS")
        verbose_name_plural = _("Paquetes Turísticos CMS")
        ordering = ['-es_destacado', 'titulo']

    def __str__(self):
        return f"{self.titulo}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)

class ArticuloBlog(models.Model):
    id_articulo = models.AutoField(primary_key=True, verbose_name=_("ID Artículo"))
    titulo = models.CharField(_("Título del Artículo"), max_length=255, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    contenido = models.TextField(_("Contenido del Artículo"))
    extracto = models.TextField(_("Extracto o Resumen"), blank=True)
    fecha_publicacion = models.DateTimeField(_("Fecha de Publicación"), null=True, blank=True, help_text=_("Si está en blanco y el estado es 'Publicado', se usará la fecha actual."))
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    imagen_destacada = models.ImageField(_("Imagen Destacada"), upload_to='cms/blog/', blank=True, null=True)
    estado = models.CharField(_("Estado"), max_length=3, choices=PaginaCMS.EstadoPublicacion.choices, default=PaginaCMS.EstadoPublicacion.BORRADOR)
    permitir_comentarios = models.BooleanField(_("Permitir Comentarios"), default=True)
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)
    fuente = models.CharField(_("Fuente de la Información"), max_length=255, blank=True, null=True, help_text=_("Origen de la información, ej: email del proveedor."))
    categoria_conocimiento = models.CharField(_("Categoría de Conocimiento"), max_length=100, blank=True, null=True, help_text=_("Categoría para la base de conocimiento interna."))

    class Meta:
        verbose_name = _("Artículo de Blog")
        verbose_name_plural = _("Artículos de Blog")
        ordering = ['-fecha_publicacion', '-fecha_creacion']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        if self.estado == PaginaCMS.EstadoPublicacion.PUBLICADO and not self.fecha_publicacion:
            self.fecha_publicacion = timezone.now()
        super().save(*args, **kwargs)

class Testimonio(models.Model):
    id_testimonio = models.AutoField(primary_key=True, verbose_name=_("ID Testimonio"))
    nombre_cliente = models.CharField(_("Nombre del Cliente"), max_length=150, validators=[validar_no_vacio_o_espacios])
    texto_testimonio = models.TextField(_("Texto del Testimonio"), validators=[validar_no_vacio_o_espacios])
    calificacion = models.PositiveSmallIntegerField(_("Calificación (1-5)"), null=True, blank=True, choices=[(i, str(i)) for i in range(1, 6)])
    fecha_recibido = models.DateField(_("Fecha Recibido/Viaje"), default=timezone.now)
    
    class EstadoTestimonio(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente de Aprobación')
        APROBADO = 'APR', _('Aprobado y Visible')
        RECHAZADO = 'REC', _('Rechazado')
    
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoTestimonio.choices, default=EstadoTestimonio.PENDIENTE)
    origen = models.CharField(_("Origen del Testimonio"), max_length=50, blank=True, help_text=_("Ej: Formulario web, Email, Red social"))

    # --- Campos de Análisis por IA ---
    class SentimientoChoices(models.TextChoices):
        POSITIVO = 'POS', _('Positivo')
        NEUTRAL = 'NEU', _('Neutral')
        NEGATIVO = 'NEG', _('Negativo')

    sentimiento = models.CharField(
        _("Sentimiento (IA)"), max_length=3, choices=SentimientoChoices.choices, 
        null=True, blank=True, editable=False
    )
    puntuacion_ia = models.PositiveSmallIntegerField(
        _("Puntuación (IA, 1-10)"), null=True, blank=True, editable=False,
        help_text=_("Puntuación de 1 a 10 generada por IA.")
    )
    temas_clave = models.JSONField(
        _("Temas Clave (IA)"), null=True, blank=True, editable=False,
        help_text=_("Lista de temas o palabras clave extraídas por la IA.")
    )

    class Meta:
        verbose_name = _("Testimonio")
        verbose_name_plural = _("Testimonios")
        ordering = ['-fecha_recibido']

    def __str__(self):
        return f"Testimonio de {self.nombre_cliente} ({self.get_estado_display()})"

class MenuItemCMS(models.Model):
    titulo = models.CharField(_("Título del Enlace"), max_length=100)
    url_enlace = models.CharField(_("URL (si es externa o manual)"), max_length=255, blank=True, help_text=_("Dejar vacío si se enlaza a contenido interno."))
    pagina_enlazada = models.ForeignKey(PaginaCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Página CMS Enlazada"))
    destino_enlazado = models.ForeignKey(DestinoCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Destino CMS Enlazado"))
    paquete_enlazado = models.ForeignKey(PaqueteTuristicoCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Paquete CMS Enlazado"))
    menu_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_items', verbose_name=_("Item Padre (para submenús)"))
    orden = models.PositiveIntegerField(_("Orden de Aparición"), default=0)
    abrir_en_nueva_pestana = models.BooleanField(_("Abrir en Nueva Pestaña"), default=False)

    class UbicacionMenu(models.TextChoices):
        PRINCIPAL = 'NAV_PRINCIPAL', _('Navegación Principal')
        FOOTER_1 = 'FOOTER_1', _('Pie de Página (Columna 1)')
        FOOTER_2 = 'FOOTER_2', _('Pie de Página (Columna 2)')
        OTRO = 'OTRO', _('Otra Ubicación')

    ubicacion = models.CharField(
        _("Ubicación del Menú"),
        max_length=20,
        choices=UbicacionMenu.choices,
        default=UbicacionMenu.PRINCIPAL,
        db_index=True
    )

    class Meta:
        verbose_name = _("Item de Menú CMS")
        verbose_name_plural = _("Items de Menú CMS")
        ordering = ['ubicacion', 'orden', 'titulo']

    def __str__(self):
        return f"{self.titulo} ({self.get_ubicacion_display()})"

    def get_url(self):
        if self.url_enlace:
            return self.url_enlace
        
        if self.pagina_enlazada:
            try:
                return reverse('core:pagina_cms_detalle', kwargs={'slug': self.pagina_enlazada.slug})
            except NoReverseMatch: 
                return f"/paginas/{self.pagina_enlazada.slug}/" 
        
        if self.destino_enlazado:
            try: 
                return reverse('core:destino_cms_detalle', kwargs={'slug': self.destino_enlazado.slug})
            except NoReverseMatch:
                 return f"/destinos/{self.destino_enlazado.slug}/" 
        
        if self.paquete_enlazado:
            try: 
                return reverse('core:paquete_cms_detalle', kwargs={'slug': self.paquete_enlazado.slug})
            except NoReverseMatch:
                return f"/paquetes/{self.paquete_enlazado.slug}/"
        return "#"

    def clean(self):
        enlaces_internos = [
            self.pagina_enlazada,
            self.destino_enlazado,
            self.paquete_enlazado,
        ]
        enlaces_definidos = sum(1 for enlace in enlaces_internos if enlace is not None)

        if self.url_enlace and enlaces_definidos > 0:
            raise ValidationError(_("No puede especificar una URL manual y un enlace a contenido interno al mismo tiempo."))
        if not self.url_enlace and enlaces_definidos == 0:
            pass 
        if enlaces_definidos > 1:
            raise ValidationError(_("Solo puede enlazar a un tipo de contenido interno a la vez."))

class FormularioContactoCMS(models.Model):
    id_envio = models.AutoField(primary_key=True, verbose_name=_("ID Envío"))
    nombre_completo = models.CharField(_("Nombre Completo"), max_length=150)
    email = models.EmailField(_("Correo Electrónico"))
    telefono = models.CharField(_("Teléfono"), max_length=30, blank=True)
    asunto = models.CharField(_("Asunto"), max_length=200, blank=True)
    mensaje = models.TextField(_("Mensaje"))
    fecha_envio = models.DateTimeField(_("Fecha de Envío"), auto_now_add=True)
    ip_origen = models.GenericIPAddressField(_("Dirección IP de Origen"), null=True, blank=True)
    
    class EstadoLectura(models.TextChoices):
        NO_LEIDO = 'NOL', _('No Leído')
        LEIDO = 'LEI', _('Leído')
        PROCESADO = 'PRO', _('Procesado/Respondido')
        SPAM = 'SPM', _('Spam')
    
    estado_lectura = models.CharField(_("Estado de Lectura"), max_length=3, choices=EstadoLectura.choices, default=EstadoLectura.NO_LEIDO)

    class Meta:
        verbose_name = _("Envío de Formulario de Contacto")
        verbose_name_plural = _("Envíos de Formularios de Contacto")
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"Envío de {self.nombre_completo} ({self.email}) el {self.fecha_envio.strftime('%Y-%m-%d %H:%M')}"

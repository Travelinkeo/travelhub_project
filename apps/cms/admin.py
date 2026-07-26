from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import Articulo, GuiaDestino, KBArticle, KBCategory, PostRedesSociales


@admin.register(Articulo)
class ArticuloAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """ArticuloAdmin."""

    list_display = ("titulo", "destino", "estado", "fecha_creacion", "generado_por_ia")
    list_filter = ("estado", "generado_por_ia", "destino")
    search_fields = ("titulo", "contenido", "destino")
    prepopulated_fields = {"slug": ("titulo",)}


@admin.register(GuiaDestino)
class GuiaDestinoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """GuiaDestinoAdmin."""

    list_display = ("nombre", "mejor_epoca", "idioma")
    search_fields = ("nombre", "descripcion")


@admin.register(PostRedesSociales)
class PostRedesSocialesAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """PostRedesSocialesAdmin."""

    list_display = ("plataforma", "articulo", "publicado", "fecha_programada")
    list_filter = ("plataforma", "publicado")


@admin.register(KBCategory)
class KBCategoryAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """KBCategoryAdmin."""

    list_display = ("name", "sort_order", "article_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def article_count(self, obj):
        """article_count."""
        return obj.articles.count()

    article_count.short_description = "Artículos"


@admin.register(KBArticle)
class KBArticleAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """KBArticleAdmin."""

    list_display = ("title", "category", "is_public", "is_published", "view_count", "created_at")
    list_filter = ("is_public", "is_published", "category")
    search_fields = ("title", "content", "tags")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = (
        "view_count",
        "helpful_count",
        "not_helpful_count",
        "created_at",
        "updated_at",
    )

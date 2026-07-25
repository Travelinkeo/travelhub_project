"""Vistas (views) de la aplicación cms.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView, View

from core.api import SaaSMixin, get_user_active_agency
from core.middleware import get_current_agency

from ..models import KBArticle, KBCategory

logger = logging.getLogger(__name__)


class KBListView(TemplateView):
    """Página pública de la Knowledge Base (lista de categorías + artículos)."""

    template_name = "cms/kb/list.html"

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        ctx = super().get_context_data(**kwargs)
        agencia = get_current_agency()
        if not agencia:
            return ctx
        ctx["categories"] = KBCategory.objects.filter(agencia=agencia).prefetch_related(
            "articles"
        )
        ctx["recent_articles"] = KBArticle.objects.filter(
            agencia=agencia, is_public=True, is_published=True
        ).order_by("-published_at")[:5]
        ctx["featured_articles"] = KBArticle.objects.filter(
            agencia=agencia, is_public=True, is_published=True
        ).order_by("-view_count")[:3]
        return ctx


class KBSearchView(TemplateView):
    """Búsqueda full-text sobre artículos públicos."""

    template_name = "cms/kb/search.html"

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        agencia = get_current_agency()
        if not agencia:
            return ctx

        ctx["query"] = q
        if q:
            articles = KBArticle.objects.filter(
                agencia=agencia, is_public=True, is_published=True
            ).filter(
                Q(title__icontains=q)
                | Q(content__icontains=q)
                | Q(tags__icontains=q)
            )
            ctx["results"] = articles
            ctx["result_count"] = articles.count()
        else:
            ctx["results"] = KBArticle.objects.none()
            ctx["result_count"] = 0
        return ctx


class KBDetailView(TemplateView):
    """Detalle de un artículo de la KB."""

    template_name = "cms/kb/detail.html"

    def get(self, request, *args, **kwargs):
        # get: Get. Args: según implementación. Returns: según implementación.
        agencia = get_current_agency()
        article = get_object_or_404(
            KBArticle,
            agencia=agencia,
            slug=kwargs["slug"],
            is_public=True,
            is_published=True,
        )
        # Increment view count
        KBArticle.objects.filter(pk=article.pk).update(view_count=article.view_count + 1)
        article.refresh_from_db()
        return self.render_to_response(self.get_context_data(article=article))

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        ctx = super().get_context_data(**kwargs)
        agencia = get_current_agency()
        article = kwargs["article"]
        ctx["article"] = article
        ctx["related_articles"] = KBArticle.objects.filter(
            agencia=agencia,
            category=article.category,
            is_public=True,
            is_published=True,
        ).exclude(pk=article.pk)[:3]
        return ctx


class KBHelpfulView(View):
    """Voto de útil/no útil."""

    def post(self, request, slug):
        # post: Post. Args: según implementación. Returns: según implementación.
        agencia = get_current_agency()
        article = get_object_or_404(KBArticle, agencia=agencia, slug=slug)
        action = request.POST.get("action")
        if action == "yes":
            KBArticle.objects.filter(pk=article.pk).update(
                helpful_count=article.helpful_count + 1
            )
        elif action == "no":
            KBArticle.objects.filter(pk=article.pk).update(
                not_helpful_count=article.not_helpful_count + 1
            )
        return redirect("cms:kb_detail", slug=slug)


# --- Admin Views (requires login) ---


class KBAdminListView(SaaSMixin, LoginRequiredMixin, ListView):
    """Listado de artículos KB para administración."""

    model = KBArticle
    template_name = "cms/kb/admin_list.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        agencia = get_user_active_agency(self.request.user)
        if not agencia:
            return KBArticle.objects.none()
        qs = KBArticle.objects.filter(agencia=agencia)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(content__icontains=q)
                | Q(tags__icontains=q)
            )
        cat = self.request.GET.get("category")
        if cat:
            qs = qs.filter(category_id=cat)
        return qs.order_by("-updated_at")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        ctx = super().get_context_data(**kwargs)
        agencia = get_user_active_agency(self.request.user)
        ctx["categories"] = KBCategory.objects.filter(agencia=agencia) if agencia else []
        return ctx


class KBArticleCreateView:
    """Vista para gestionar kbarticlecreate. Uso: instanciar según necesidad del dominio.
    """
    model = KBArticle
    template_name = "cms/kb/admin_form.html"
    fields = ["title", "slug", "content", "category", "tags", "is_public", "is_published"]
    success_url = reverse_lazy("cms:kb_admin_list")

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        agencia = get_user_active_agency(self.request.user)
        if agencia:
            form.instance.agencia = agencia
        if form.instance.is_published and not form.instance.published_at:
            form.instance.published_at = timezone.now()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        ctx = super().get_context_data(**kwargs)
        ctx["is_new"] = True
        return ctx


class KBArticleUpdateView:
    """Vista para gestionar kbarticleupdate. Uso: instanciar según necesidad del dominio.
    """
    model = KBArticle
    template_name = "cms/kb/admin_form.html"
    fields = ["title", "slug", "content", "category", "tags", "is_public", "is_published"]
    success_url = reverse_lazy("cms:kb_admin_list")

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        agencia = get_user_active_agency(self.request.user)
        if not agencia:
            return KBArticle.objects.none()
        return KBArticle.objects.filter(agencia=agencia)

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        if form.instance.is_published and not form.instance.published_at:
            form.instance.published_at = timezone.now()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        ctx = super().get_context_data(**kwargs)
        ctx["is_new"] = False
        return ctx


class KBArticleDeleteView:
    """Vista para gestionar kbarticledelete. Uso: instanciar según necesidad del dominio.
    """
    model = KBArticle
    success_url = reverse_lazy("cms:kb_admin_list")

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        agencia = get_user_active_agency(self.request.user)
        if not agencia:
            return KBArticle.objects.none()
        return KBArticle.objects.filter(agencia=agencia)

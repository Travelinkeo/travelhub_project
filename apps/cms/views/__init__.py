import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from core.api import SaaSMixin, get_user_active_agency

from ..forms import ArticuloForm, GuiaDestinoForm
from ..models import Articulo, GuiaDestino
from ..services.cms_ai_service import CMSContentService
from ..services.content_service import AIContentService

logger = logging.getLogger(__name__)


class ContentDashboardView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Articulo
    template_name = "cms/dashboard.html"
    context_object_name = "articulos"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agencia = get_user_active_agency(self.request.user)
        if agencia:
            context["guias"] = GuiaDestino.objects.filter(agencia=agencia)
        else:
            context["guias"] = GuiaDestino.objects.none()
        return context


class GenerateArticleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        destination = request.POST.get("destination")
        keywords = request.POST.get("keywords", "")

        if not destination:
            return HttpResponse("Destino requerido.", status=400)

        service = AIContentService()
        try:
            articulo = service.generate_article(destination, keywords)
            response = render(request, "cms/partials/article_card.html", {"articulo": articulo})
            response["HX-Trigger"] = json.dumps(
                {"notify": {"message": "¡Artículo generado con éxito!", "type": "success"}}
            )
            return response
        except Exception as e:
            response = HttpResponse(f"Error: {e}", status=500)
            response["HX-Trigger"] = json.dumps(
                {"notify": {"message": f"Error: {str(e)}", "type": "error"}}
            )
            return response


class GenerateSocialPostsView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        service = AIContentService()
        try:
            posts = service.generate_social_posts(pk)
            return render(request, "cms/partials/social_posts.html", {"posts": posts})
        except Exception as e:
            return HttpResponse(f"Error: {e}", status=500)


class ArticuloCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = Articulo
    form_class = ArticuloForm
    template_name = "cms/articulo_form.html"
    success_url = reverse_lazy("cms:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Artículo creado exitosamente.")
        return super().form_valid(form)


class ArticuloUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = Articulo
    form_class = ArticuloForm
    template_name = "cms/articulo_form.html"
    success_url = reverse_lazy("cms:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Artículo actualizado exitosamente.")
        return super().form_valid(form)


class ArticuloDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = Articulo
    template_name = "cms/confirm_delete.html"
    success_url = reverse_lazy("cms:dashboard")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Artículo eliminado.")
        return super().delete(request, *args, **kwargs)


class GuiaDestinoCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = GuiaDestino
    form_class = GuiaDestinoForm
    template_name = "cms/guia_destino_form.html"
    success_url = reverse_lazy("cms:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Guía de destino creada exitosamente.")
        return super().form_valid(form)


class GuiaDestinoUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = GuiaDestino
    form_class = GuiaDestinoForm
    template_name = "cms/guia_destino_form.html"
    success_url = reverse_lazy("cms:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Guía de destino actualizada exitosamente.")
        return super().form_valid(form)


class GuiaDestinoDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = GuiaDestino
    template_name = "cms/confirm_delete.html"
    success_url = reverse_lazy("cms:dashboard")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Guía de destino eliminada.")
        return super().delete(request, *args, **kwargs)


class AIGenerateSuggestionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        field = request.POST.get("field")
        context = request.POST.get("context")

        if not field or not context:
            return JsonResponse({"error": "Faltan parámetros"}, status=400)

        service = CMSContentService()
        try:
            if field == "titulo":
                prompt = f"Sugiere un título de blog profesional e inspirador basado en: {context}. Retorna solo el texto del título."
            elif field == "resumen":
                prompt = f"Escribe un resumen SEO de 2 líneas para un artículo sobre: {context}. Retorna solo el texto del resumen."
            elif field == "nombre_destino":
                prompt = f"Sugiere un nombre comercial o atractivo para un destino turístico basado en: {context}. Retorna solo el nombre."
            elif field == "descripcion_guia":
                prompt = f"Escribe una descripción introductoria cautivadora para una guía de viajes de: {context}. Máximo 3 líneas."
            elif field == "caption":
                result = service.generate_social_post(context)
                if isinstance(result, str):
                    data = json.loads(result)
                    return JsonResponse({"suggestion": data.get("caption", "")})
                return JsonResponse({"suggestion": result.get("caption", "")})
            else:
                return JsonResponse({"error": "Campo no soportado"}, status=400)

            response = service.client.models.generate_content(
                model=service.model_name, contents=prompt
            )
            return JsonResponse({"suggestion": response.text.strip()})

        except Exception as e:
            logger.exception(f"Error generando sugerencia para {field}")
            return JsonResponse({"error": str(e)}, status=500)

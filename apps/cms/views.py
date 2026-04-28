from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Articulo, GuiaDestino, PostRedesSociales
from .forms import ArticuloForm, GuiaDestinoForm
from .services.cms_ai_service import CMSContentService
from django.http import HttpResponse, JsonResponse
import json
import logging

logger = logging.getLogger(__name__)

class ContentDashboardView(LoginRequiredMixin, ListView):
    model = Articulo
    template_name = 'cms/dashboard.html'
    context_object_name = 'articulos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['guias'] = GuiaDestino.objects.all()
        return context

class GenerateArticleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        destination = request.POST.get('destination')
        keywords = request.POST.get('keywords', '')
        
        if not destination:
            return HttpResponse("Destino requerido.", status=400)
            
        service = AIContentService()
        try:
            articulo = service.generate_article(destination, keywords)
            response = render(request, 'cms/partials/article_card.html', {'articulo': articulo})
            response['HX-Trigger'] = json.dumps({"notify": {"message": "¡Artículo generado con éxito!", "type": "success"}})
            return response
        except Exception as e:
            response = HttpResponse(f"Error: {e}", status=500)
            response['HX-Trigger'] = json.dumps({"notify": {"message": f"Error: {str(e)}", "type": "error"}})
            return response

class GenerateSocialPostsView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        service = AIContentService()
        try:
            posts = service.generate_social_posts(pk)
            return render(request, 'cms/partials/social_posts.html', {'posts': posts})
        except Exception as e:
            return HttpResponse(f"Error: {e}", status=500)

# --- Articulo CRUD ---

class ArticuloCreateView(LoginRequiredMixin, CreateView):
    model = Articulo
    form_class = ArticuloForm
    template_name = 'cms/articulo_form.html'
    success_url = reverse_lazy('cms:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Artículo creado exitosamente.")
        return super().form_valid(form)

class ArticuloUpdateView(LoginRequiredMixin, UpdateView):
    model = Articulo
    form_class = ArticuloForm
    template_name = 'cms/articulo_form.html'
    success_url = reverse_lazy('cms:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Artículo actualizado exitosamente.")
        return super().form_valid(form)

class ArticuloDeleteView(LoginRequiredMixin, DeleteView):
    model = Articulo
    template_name = 'cms/confirm_delete.html'
    success_url = reverse_lazy('cms:dashboard')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Artículo eliminado.")
        return super().delete(request, *args, **kwargs)

# --- GuiaDestino CRUD ---

class GuiaDestinoCreateView(LoginRequiredMixin, CreateView):
    model = GuiaDestino
    form_class = GuiaDestinoForm
    template_name = 'cms/guia_destino_form.html'
    success_url = reverse_lazy('cms:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Guía de destino creada exitosamente.")
        return super().form_valid(form)

class GuiaDestinoUpdateView(LoginRequiredMixin, UpdateView):
    model = GuiaDestino
    form_class = GuiaDestinoForm
    template_name = 'cms/guia_destino_form.html'
    success_url = reverse_lazy('cms:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Guía de destino actualizada exitosamente.")
        return super().form_valid(form)

class GuiaDestinoDeleteView(LoginRequiredMixin, DeleteView):
    model = GuiaDestino
    template_name = 'cms/confirm_delete.html'
    success_url = reverse_lazy('cms:dashboard')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Guía de destino eliminada.")
        return super().delete(request, *args, **kwargs)

class AIGenerateSuggestionView(LoginRequiredMixin, View):
    """
    Endpoint para generar sugerencias específicas de campos (Título, Resumen, etc.)
    mediante Gemini 2.0 Flash.
    """
    def post(self, request, *args, **kwargs):
        field = request.POST.get('field')
        context = request.POST.get('context')
        
        if not field or not context:
            return JsonResponse({"error": "Faltan parámetros"}, status=400)
            
        service = CMSContentService()
        try:
            if field == 'titulo':
                prompt = f"Sugiere un título de blog profesional e inspirador basado en: {context}. Retorna solo el texto del título."
            elif field == 'resumen':
                prompt = f"Escribe un resumen SEO de 2 líneas para un artículo sobre: {context}. Retorna solo el texto del resumen."
            elif field == 'nombre_destino':
                prompt = f"Sugiere un nombre comercial o atractivo para un destino turístico basado en: {context}. Retorna solo el nombre."
            elif field == 'descripcion_guia':
                prompt = f"Escribe una descripción introductoria cautivadora para una guía de viajes de: {context}. Máximo 3 líneas."
            elif field == 'caption':
                # Usamos el método existente para social posts
                result = service.generate_social_post(context)
                if isinstance(result, str):
                    import json
                    data = json.loads(result)
                    return JsonResponse({"suggestion": data.get('caption', '')})
                return JsonResponse({"suggestion": result.get('caption', '')})
            else:
                return JsonResponse({"error": "Campo no soportado"}, status=400)

            # Para campos genéricos usamos el modelo directamente
            response = service.model.generate_content(prompt)
            return JsonResponse({"suggestion": response.text.strip()})
            
        except Exception as e:
            logger.exception(f"Error generando sugerencia para {field}")
            return JsonResponse({"error": str(e)}, status=500)

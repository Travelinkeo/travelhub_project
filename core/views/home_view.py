from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Función: HomeView."""
    template_name = "core/home.html"

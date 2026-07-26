from django.views.generic import TemplateView


class HomeView(TemplateView):
    """HomeView."""

    template_name = "core/home.html"

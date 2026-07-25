from django.shortcuts import render


def developer_portal(request):
    """Función: developer portal."""
    return render(request, "marketing/dev_portal.html")

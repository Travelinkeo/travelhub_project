from django.shortcuts import render
from django.db.models import Q
from core.models.wiki import WikiArticulo
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

@login_required
@require_http_methods(["GET"])
def search_wiki_context(request):
    """
    Busca artículos de Wiki basados en el contexto (tags).
    Retorna un parcial HTML para HTMX.
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return render(request, 'core/wiki/partials/results.html', {'articulos': []})

    # Búsqueda simple: Título o Tags que contengan la query
    # Nota: JSONField lookup __icontains funciona en SQLite/Postgres para listas simples.
    articulos = WikiArticulo.objects.filter(
        Q(titulo__icontains=query) | 
        Q(tags__icontains=query),
        activo=True
    ).order_by('-updated_at')[:3] # Limitar a 3 resultados

    return render(request, 'core/wiki/partials/results.html', {'articulos': articulos})

import os
from django.shortcuts import render
from django.http import Http404, HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from pathlib import Path

# Intentar importar markdown, si no instalamos o usamos fallback simple
try:
    import markdown
except ImportError:
    markdown = None

@login_required
def wiki_gds_list(request):
    """
    Lista las categorías de la Wiki GDS (carpetas en docs/wiki/GDS).
    """
    wiki_root = Path(settings.BASE_DIR) / 'docs' / 'wiki' / 'GDS'
    categories = []
    
    if wiki_root.exists():
        for entry in os.scandir(wiki_root):
            if entry.is_dir():
                categories.append({
                    'name': entry.name,
                    'path': entry.name
                })
    
    return render(request, 'core/wiki/wiki_list.html', {
        'categories': categories,
        'title': 'Wiki GDS - Categorías'
    })

@login_required
def wiki_gds_reader(request, category, filename='README.md'):
    """
    Lee y renderiza un archivo Markdown de la Wiki GDS.
    """
    wiki_path = Path(settings.BASE_DIR) / 'docs' / 'wiki' / 'GDS' / category / filename
    
    if not wiki_path.exists() or not wiki_path.is_file():
        raise Http404("El artículo de la Wiki no existe.")
    
    with open(wiki_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Renderizar Markdown a HTML
    if markdown:
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables', 'toc'])
    else:
        # Fallback ultra-básico (solo saltos de línea y negritas simples)
        html_content = content.replace('\n', '<break>').replace('**', '<b>').replace('## ', '<h2>').replace('# ', '<h1>')
        html_content = html_content.replace('<break>', '<br>')
        html_content = f"<div class='alert alert-warning'>Módulo 'markdown' no instalado. Mostrando versión simplificada.</div>{html_content}"

    # Navegación del sidebar (otros archivos en la misma carpeta)
    other_articles = []
    for entry in os.scandir(wiki_path.parent):
        if entry.is_file() and entry.name.endswith('.md'):
            other_articles.append({
                'name': entry.name.replace('.md', ''),
                'filename': entry.name,
                'active': entry.name == filename
            })

    return render(request, 'core/wiki/wiki_reader.html', {
        'content': html_content,
        'category': category,
        'filename': filename,
        'articles': other_articles,
        'title': f"Wiki GDS - {category}"
    })

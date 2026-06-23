import logging
import os
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

# Intentar importar markdown, si no instalamos o usamos fallback simple
try:
    import markdown
except ImportError:
    markdown = None

logger = logging.getLogger(__name__)

try:
    import bleach
except ImportError:
    bleach = None

ALLOWED_TAGS = [
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "br",
    "hr",
    "ul",
    "ol",
    "li",
    "a",
    "strong",
    "em",
    "b",
    "i",
    "code",
    "pre",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "img",
    "div",
    "span",
    "del",
    "sup",
    "sub",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "title", "width", "height"],
    "th": ["align"],
    "td": ["align"],
    "code": ["class"],
    "pre": ["class"],
    "div": ["class"],
    "span": ["class"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def _sanitize_html(html_content):
    if bleach:
        return bleach.clean(
            html_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,
        )
    return html_content


@login_required
def wiki_gds_list(request):
    """
    Lista las categorías de la Wiki GDS (carpetas en docs/wiki/GDS).
    """
    wiki_root = Path(settings.BASE_DIR) / "docs" / "wiki" / "GDS"
    categories = []

    if wiki_root.exists():
        for entry in os.scandir(wiki_root):
            if entry.is_dir():
                categories.append({"name": entry.name, "path": entry.name})

    return render(
        request,
        "core/wiki/wiki_list.html",
        {"categories": categories, "title": "Wiki GDS - Categorías"},
    )


@login_required
def wiki_gds_reader(request, category, filename="README.md"):
    """
    Lee y renderiza un archivo Markdown de la Wiki GDS.
    """
    wiki_root = Path(settings.BASE_DIR) / "docs" / "wiki" / "GDS"
    wiki_path = (wiki_root / category / filename).resolve()

    if not str(wiki_path).startswith(str(wiki_root.resolve())):
        raise Http404("El artículo de la Wiki no existe.")

    if not wiki_path.exists() or not wiki_path.is_file():
        raise Http404("El artículo de la Wiki no existe.")

    with open(wiki_path, encoding="utf-8") as f:
        content = f.read()

    # Renderizar Markdown a HTML
    if markdown:
        html_content = markdown.markdown(content, extensions=["fenced_code", "tables", "toc"])
        html_content = _sanitize_html(html_content)
    else:
        # Fallback ultra-básico (solo saltos de línea y negritas simples)
        html_content = (
            content.replace("\n", "<break>")
            .replace("**", "<b>")
            .replace("## ", "<h2>")
            .replace("# ", "<h1>")
        )
        html_content = html_content.replace("<break>", "<br>")
        html_content = f"<div class='alert alert-warning'>Módulo 'markdown' no instalado. Mostrando versión simplificada.</div>{html_content}"

    # Navegación del sidebar (otros archivos en la misma carpeta)
    other_articles = []
    for entry in os.scandir(wiki_path.parent):
        if entry.is_file() and entry.name.endswith(".md"):
            other_articles.append(
                {
                    "name": entry.name.replace(".md", ""),
                    "filename": entry.name,
                    "active": entry.name == filename,
                }
            )

    return render(
        request,
        "core/wiki/wiki_reader.html",
        {
            "content": html_content,
            "category": category,
            "filename": filename,
            "articles": other_articles,
            "title": f"Wiki GDS - {category}",
        },
    )


@login_required
def wiki_search(request):
    """
    Busca artículos de la Wiki GDS usando el parámetro de consulta 'q'
    y retorna fragmentos formateados como HTML.
    """
    query = request.GET.get("q", "").strip().lower()
    articulos = []

    if len(query) >= 3:
        wiki_root = Path(settings.BASE_DIR) / "docs" / "wiki" / "GDS"
        if wiki_root.exists():
            # Buscamos en todos los archivos .md recursivamente
            for root, _dirs, files in os.walk(wiki_root):
                for file in files:
                    if file.endswith(".md"):
                        file_path = Path(root) / file
                        category = (
                            file_path.parent.name if file_path.parent != wiki_root else "General"
                        )

                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()
                        except (OSError, UnicodeDecodeError) as e:
                            logger.debug("No se pudo leer wiki file %s: %s", file_path, e)
                            continue

                        # Buscamos secciones usando regex para dividir por títulos
                        pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
                        matches = list(pattern.finditer(content))

                        sections = []
                        if not matches:
                            sections.append(
                                {
                                    "titulo": f"{category} - {file.replace('.md', '')}",
                                    "contenido_raw": content,
                                }
                            )
                        else:
                            for i, match in enumerate(matches):
                                header_title = match.group(2).strip()
                                start_pos = match.end()
                                end_pos = (
                                    matches[i + 1].start() if i + 1 < len(matches) else len(content)
                                )
                                section_body = content[start_pos:end_pos].strip()

                                sections.append(
                                    {
                                        "titulo": f"{category} - {header_title}",
                                        "contenido_raw": section_body,
                                    }
                                )

        for sec in sections:
            if query in sec["titulo"].lower() or query in sec["contenido_raw"].lower():
                if markdown:
                    html_content = markdown.markdown(
                        sec["contenido_raw"], extensions=["fenced_code", "tables"]
                    )
                    html_content = _sanitize_html(html_content)
                else:
                    html_content = sec["contenido_raw"].replace("\n", "<br>").replace("**", "<b>")

                articulos.append({"titulo": sec["titulo"], "contenido": html_content})

            if len(articulos) >= 10:
                break

    return render(request, "core/wiki/partials/results.html", {"articulos": articulos[:5]})

"""
Knowledge Base — Visor de documentación pública.

Sirve archivos Markdown de docs/ como HTML con navegación.
Ideal para docs.travelhub.cc (subdominio independiente).
"""

import os
import re
from pathlib import Path

import markdown
from django.conf import settings
from django.http import HttpResponseNotFound
from django.shortcuts import render
from django.views.decorators.http import require_GET


def _get_docs_tree(base_dir):
    """Construye árbol de navegación desde la estructura de docs/."""
    docs_path = Path(base_dir) / "docs"
    if not docs_path.exists():
        return []

    tree = []
    for item in sorted(docs_path.iterdir()):
        if item.is_file() and item.suffix == ".md" and item.name != "INDEX.md":
            tree.append(
                {
                    "title": _title_from_filename(item.stem),
                    "slug": item.stem.lower(),
                    "path": item.name,
                    "type": "page",
                }
            )
        elif item.is_dir() and not item.name.startswith("_"):
            children = []
            for sub in sorted(item.iterdir()):
                if sub.suffix == ".md":
                    children.append(
                        {
                            "title": _title_from_filename(sub.stem),
                            "slug": f"{item.name}/{sub.stem.lower()}",
                            "path": f"{item.name}/{sub.name}",
                            "type": "page",
                        }
                    )
            if children:
                tree.append(
                    {
                        "title": item.name.replace("_", " ").title(),
                        "slug": item.name,
                        "type": "section",
                        "children": children,
                    }
                )
    return tree


def _title_from_filename(stem):
    """Convierte nombre de archivo en título legible."""
    title = stem.replace("_", " ").replace("-", " ")
    # Capitalizar palabras significativas
    return " ".join(
        w.capitalize()
        if w.lower()
        not in ("de", "del", "la", "los", "el", "y", "en", "con", "por", "para", "un", "una")
        else w
        for w in title.split()
    )


@require_GET
def docs_index(request):
    """Página principal de la documentación."""
    docs_path = settings.BASE_DIR / "docs"
    index_path = docs_path / "INDEX.md"

    content = ""
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            content = markdown.markdown(f.read(), extensions=["fenced_code", "tables", "extra"])

    tree = _get_docs_tree(settings.BASE_DIR)
    return render(
        request,
        "docs/base_docs.html",
        {
            "content": content,
            "tree": tree,
            "current_title": "Documentación TravelHub",
            "page_title": "Inicio",
        },
    )


@require_GET
def docs_page(request, path):
    """Renderiza una página de documentación desde un archivo .md."""
    docs_path = settings.BASE_DIR / "docs"
    # Seguridad: evitar path traversal
    clean_path = os.path.normpath(path)
    if ".." in clean_path or clean_path.startswith("/"):
        return HttpResponseNotFound("Invalid path")

    file_path = docs_path / clean_path
    # Si no tiene extensión, probar .md
    if not file_path.suffix:
        file_path = file_path.with_suffix(".md")

    if not file_path.exists() or not str(file_path).startswith(str(docs_path)):
        return HttpResponseNotFound("Documento no encontrado")

    with open(file_path, encoding="utf-8") as f:
        raw = f.read()

    # Extraer título del primer H1
    title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
    page_title = title_match.group(1).strip() if title_match else file_path.stem

    content = markdown.markdown(
        raw,
        extensions=[
            "fenced_code",
            "tables",
            "extra",
            "codehilite",
            "toc",
        ],
    )

    tree = _get_docs_tree(settings.BASE_DIR)
    toc = _extract_toc(raw)

    return render(
        request,
        "docs/base_docs.html",
        {
            "content": content,
            "tree": tree,
            "current_title": page_title,
            "page_title": page_title,
            "toc": toc,
            "edit_url": f"https://github.com/armandocode/travelhub/edit/main/docs/{clean_path}",
        },
    )


def _extract_toc(markdown_text):
    """Extrae H2/H3 del markdown para tabla de contenidos."""
    toc = []
    for line in markdown_text.split("\n"):
        h2 = re.match(r"^##\s+(.+)$", line)
        h3 = re.match(r"^###\s+(.+)$", line)
        if h2:
            title = h2.group(1).strip()
            slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title).lower().replace(" ", "-")
            toc.append({"title": title, "slug": slug, "level": 2})
        elif h3:
            title = h3.group(1).strip()
            slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title).lower().replace(" ", "-")
            toc.append({"title": title, "slug": slug, "level": 3})
    return toc

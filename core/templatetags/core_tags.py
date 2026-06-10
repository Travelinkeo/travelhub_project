from django import template
from django.utils.safestring import mark_safe

from core.validators import sanitize_html

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiplica el valor por el argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def sanitize_html_filter(value, tags=None):
    """
    Sanitiza HTML para prevenir XSS.
    Uso: {{ contenido|sanitize_html_filter|safe }}
    """
    if not value:
        return ""
    cleaned = sanitize_html(value)
    return mark_safe(cleaned)

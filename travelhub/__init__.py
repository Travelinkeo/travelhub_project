"""Inicialización de TravelHub"""

# 🛡️ SAFE LOCALE MONKEY PATCH (SRE L3)
# Aplicado ANTES de cualquier código de app para interceptar setlocale
# que falla en contenedores sin locale es_ES.UTF-8 instalado.
import locale as _locale
import logging as _logging

_locale_logger = _logging.getLogger("travelhub.locale")

try:
    _original_setlocale = _locale.setlocale

    def _safe_setlocale(category, locale_name=None):
        try:
            return _original_setlocale(category, locale_name)
        except Exception as e:
            _locale_logger.debug(f"Intercepted unsupported locale '{locale_name}': {e}")
            try:
                return _original_setlocale(category, "")
            except Exception:
                try:
                    return _original_setlocale(category, "C")
                except Exception:
                    return "C"

    _locale.setlocale = _safe_setlocale
    _locale_logger.debug("Globally patched locale.setlocale to prevent unsupported locale crashes.")
except Exception as e:
    _locale_logger.warning(f"Failed to patch locale.setlocale: {e}")

# Cargar Celery app para que Django lo reconozca
try:
    from .celery import app as celery_app  # noqa: E402

    __all__ = ("celery_app",)
except ImportError:
    # Celery es opcional
    pass

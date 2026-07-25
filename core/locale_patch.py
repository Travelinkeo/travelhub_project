# core/locale_patch.py
"""Parche de seguridad para locale.setlocale en entornos Docker."""

import locale
import logging

logger = logging.getLogger(__name__)


def apply_locale_patch():
    """
    Aplica un parche de seguridad al runtime de locale.setlocale (SRE L3).
    Esto intercepta llamadas globales de setlocale que puedan arrojar
    'unsupported locale setting' en sistemas sin locale configurado (como Docker minimalista).
    """
    if getattr(locale.setlocale, "_is_safe_patch", False):
        logger.debug("locale.setlocale ya parchado, omitiendo doble patch.")
        return

    try:
        original_setlocale = locale.setlocale

        def safe_setlocale(category, locale_name=None):
            """Función: safe setlocale."""
            try:
                return original_setlocale(category, locale_name)
            except Exception as e:
                logger.warning(
                    f"⚠️ [SRE L3 Locale Patch] Blocked unsupported locale setting '{locale_name}': {e}"
                )
                try:
                    return original_setlocale(category, "")
                except Exception:
                    try:
                        return original_setlocale(category, "C")
                    except Exception:
                        return "C"

        safe_setlocale._is_safe_patch = True
        locale.setlocale = safe_setlocale
        logger.info(
            "✅ [SRE L3] Global locale.setlocale monkey patch applied successfully via ready()."
        )
    except Exception as e_patch:
        logger.error(f"❌ [SRE L3] Failed to apply locale monkey patch: {e_patch}")

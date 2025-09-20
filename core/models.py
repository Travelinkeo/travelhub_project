"""Archivo monolítico de modelos (LEGACY / FASE 2 - Obsoleto).

Todos los modelos han sido migrados a los submódulos correspondientes dentro de `core/models/`.
Este archivo se mantiene temporalmente para evitar problemas con el historial de git y
se eliminará en una futura iteración.

No añadir ningún código nuevo aquí.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# SHIM: Se define el validador directamente aquí para dar compatibilidad a la migración 0001
# que espera encontrar la función en `core.models.validar_no_vacio_o_espacios`
def validar_no_vacio_o_espacios(value):
    if isinstance(value, str) and not value.strip():
        raise ValidationError(_('Este campo no puede consistir únicamente en espacios en blanco.'))

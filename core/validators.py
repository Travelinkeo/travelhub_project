# Archivo: core/validators.py

import os

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_file_size(value):
    """Valida que el tamaño del archivo no exceda un límite (ej. 5MB)."""
    limit = 5 * 1024 * 1024  # 5 MB
    if value.size > limit:
        raise ValidationError(_('El archivo es demasiado grande. El tamaño no puede exceder los 5 MB.'))

def validate_file_extension(value):
    """Valida que la extensión del archivo esté en una lista permitida."""
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.txt', '.eml']
    if ext.lower() not in valid_extensions:
        raise ValidationError(_('Extensión de archivo no válida. Solo se permiten archivos PDF, TXT y EML.'))

def antivirus_hook(value):
    """Hook para una futura integración de escaneo de antivirus.
    
    Actualmente es un placeholder y no realiza ninguna operación.
    En el futuro, aquí se podría integrar una llamada a un servicio como ClamAV.
    """
    # Ejemplo de futura implementación:
    # try:
    #     import clamd
    #     cd = clamd.ClamdUnixSocket()
    #     scan_result = cd.instream(value)
    #     if scan_result['stream'][0] == 'FOUND':
    #         raise ValidationError(_('Se detectó un virus en el archivo.'))
    # except Exception as e:
    #     # Loggear el error de escaneo pero no bloquear la subida
    #     # para no detener la operación si el servicio de AV está caído.
    #     logger.error(f"Error en el hook de antivirus: {e}")
    pass

def validar_no_vacio_o_espacios(value):
    if isinstance(value, str) and not value.strip():
        raise ValidationError(_('Este campo no puede consistir únicamente en espacios en blanco.'))

def validar_numero_pasaporte(value):
    """Valida que el número de pasaporte no esté vacío.

    Args:
        value (str): El valor a validar.

    Raises:
        ValidationError: Si el valor está vacío o solo contiene espacios.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(_('El número de documento no puede estar vacío.'))

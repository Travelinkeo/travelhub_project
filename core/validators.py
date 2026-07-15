import logging
import os
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

try:
    import bleach

    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

logger = logging.getLogger(__name__)


MAX_FILE_SIZE = 5 * 1024 * 1024
VALID_EXTENSIONS = [".pdf", ".txt", ".eml", ".xlsx", ".csv", ".jpg", ".jpeg", ".png"]

# MIME types permitidos por extensión
ALLOWED_MIME_TYPES = {
    ".pdf": ["application/pdf"],
    ".txt": ["text/plain"],
    ".eml": ["message/rfc822", "text/plain"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    ".csv": ["text/csv", "text/plain"],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
    ".png": ["image/png"],
}

# MB por plan SaaS
PLAN_SIZE_LIMITS_MB = {
    "FREE": 2,
    "BASIC": 5,
    "PRO": 10,
    "ENTERPRISE": 25,
}


def _sanitize_filename(name):
    """Elimina paths relativos y caracteres peligrosos del nombre de archivo."""
    name = os.path.basename(name)
    name = re.sub(r"[^\w\.\-]", "_", name)
    name = name.strip("._-")
    name = name[:200]
    return name if name else "uploaded_file"


def get_plan_size_limit(agencia=None):
    """Retorna el limite de tamano en bytes segun el plan de la agencia."""
    plan = "FREE"
    if agencia and hasattr(agencia, "plan") and agencia.plan:
        plan = agencia.plan
    limit_mb = PLAN_SIZE_LIMITS_MB.get(plan, 2)
    return limit_mb * 1024 * 1024


def validate_file_size(value, agencia=None):
    limit = get_plan_size_limit(agencia)
    limit_mb = limit / (1024 * 1024)
    if value.size > limit:
        raise ValidationError(
            _("El archivo es demasiado grande. El tamano maximo para tu plan es de %(size)d MB."),
            params={"size": int(limit_mb)},
        )


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]
    if ext.lower() not in VALID_EXTENSIONS:
        raise ValidationError(
            _("Extension de archivo no valida. Solo se permiten: %(exts)s."),
            params={"exts": ", ".join(VALID_EXTENSIONS).upper()},
        )

    # Validar magic bytes del archivo para detectar extensiones falsificadas
    MAGIC_BYTES = {
        ".pdf": b"%PDF",
        ".txt": None,
        ".eml": None,
        ".xlsx": b"PK",
        ".csv": None,
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
        ".png": b"\x89PNG",
    }

    expected_magic = MAGIC_BYTES.get(ext.lower())
    if expected_magic is not None:
        try:
            value.seek(0)
            header = value.read(4)
            value.seek(0)
            if not header.startswith(expected_magic):
                logger.warning(
                    f"Magic bytes mismatch: {value.name} tiene header {header!r}, "
                    f"esperado {expected_magic!r} para extension {ext}"
                )
                raise ValidationError(
                    _("El contenido del archivo no coincide con la extension %(ext)s."),
                    params={"ext": ext.upper()},
                )
        except (OSError, AttributeError):
            pass


def validate_filename_safe(value):
    """Valida que el nombre del archivo no contenga patrones maliciosos."""
    original = value.name
    sanitized = _sanitize_filename(original)
    if sanitized != original:
        value.name = sanitized
        logger.info(f"Nombre de archivo sanitizado: '{original}' -> '{sanitized}'")


def antivirus_hook(value):
    """
    Escanea un archivo con ClamAV si está disponible.
    Si clamd no está instalado, registra una advertencia.
    Si ClamAV detecta un virus, rechaza el archivo.
    """
    try:
        import clamd

        cd = clamd.ClamdUnixSocket()
        scan_result = cd.instream(value)
        if scan_result["stream"][0] == "FOUND":
            virus_name = scan_result["stream"][1]
            logger.error(f"Antivirus detecto amenaza: {virus_name} en archivo subido")
            raise ValidationError(
                _("El archivo contiene software malicioso detectado: %(virus)s."),
                params={"virus": virus_name},
            )
    except ImportError:
        logger.warning(
            "ClamAV (clamd) no está instalado. Las subidas de archivos NO tienen escaneo antivirus. "
            "Instala pyclamd para activar la protección."
        )
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error conectando con ClamAV durante escaneo antivirus: {e}")


def validar_no_vacio_o_espacios(value):
    if isinstance(value, str) and not value.strip():
        raise ValidationError(_("Este campo no puede consistir unicamente en espacios en blanco."))


def validar_numero_pasaporte(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(_("El numero de documento no puede estar vacio."))


ALLOWED_HTML_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
    "blockquote",
    "code",
    "pre",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "img",
]
ALLOWED_HTML_ATTRS = {
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}


def sanitize_html(value, tags=None, attributes=None):
    """
    Sanitiza HTML para prevenir XSS usando bleach.
    Si bleach no está instalado, elimina TODAS las etiquetas HTML (fallback seguro).
    """
    if not value:
        return ""
    if not HAS_BLEACH:
        logger.warning(
            "bleach no está instalado — se eliminarán TODAS las etiquetas HTML como fallback seguro"
        )
        import django.utils.html

        return django.utils.html.strip_tags(value)
    allowed_tags = tags or ALLOWED_HTML_TAGS
    allowed_attrs = attributes or ALLOWED_HTML_ATTRS
    return bleach.clean(value, tags=allowed_tags, attributes=allowed_attrs, strip=True)

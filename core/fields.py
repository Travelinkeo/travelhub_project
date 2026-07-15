"""
Custom Encrypted Field for Django

Provides field-level encryption using Fernet (symmetric encryption)
from the cryptography library.

Usage:
    from core.fields import EncryptedCharField, EncryptedTextField

    class MyModel(models.Model):
        sensitive_data = EncryptedCharField(max_length=100)
        notes = EncryptedTextField()
"""

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)


class _FernetMixin:
    """
    Mixin que centraliza la lógica de cifrado Fernet compartida por
    EncryptedCharField y EncryptedTextField.

    Usa un cache de clase ÚNICO (_fernet_instance) compartido entre
    todas las instancias, inicializado de forma lazy (al primer uso).
    """

    _fernet_instance = None

    @classmethod
    def _get_fernet(cls):
        """Retorna la instancia Fernet compartida, inicializándola si es necesario."""
        if _FernetMixin._fernet_instance is None:
            try:
                from cryptography.fernet import Fernet

                encryption_key = getattr(settings, "ENCRYPTION_KEY", None)
                if not encryption_key:
                    raise ImproperlyConfigured(
                        "ENCRYPTION_KEY es requerido para campos cifrados. "
                        "Genera uno con: "
                        'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
                    )
                _FernetMixin._fernet_instance = Fernet(encryption_key.encode())
            except ImproperlyConfigured:
                raise
            except Exception as e:
                logger.error("Error inicializando Fernet: %s", e)
                raise
        return _FernetMixin._fernet_instance

    @property
    def fernet(self):
        return self._get_fernet()

    def _encrypt(self, value: str) -> str:
        """Cifra un string. Si ya está cifrado (prefijo gAAAAA), lo devuelve tal cual."""
        if value.startswith("gAAAAA"):
            return value
        try:
            return self.fernet.encrypt(value.encode()).decode("utf-8")
        except Exception as e:
            logger.error("Error cifrando valor en campo %s: %s", self.name, e)
            raise ValueError(f"Fallo crítico al cifrar campo sensible: {e}") from e

    def _decrypt(self, value: str) -> str:
        """Descifra un string. Lanza ValueError si el token es inválido."""
        try:
            return self.fernet.decrypt(value.encode()).decode("utf-8")
        except Exception as e:
            logger.critical("Error descifrando campo %s: %s", self.name, e)
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(e)
            except ImportError:
                pass
            raise ValueError(
                f"Fallo al descifrar campo sensible '{self.name}': el token es inválido o la clave "
                f"de cifrado ha cambiado. Contacta al administrador del sistema."
            ) from e

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return self._encrypt(value)

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return self._decrypt(value)

    def to_python(self, value):
        if value is None or value == "":
            return value
        return value


class EncryptedCharField(_FernetMixin, models.CharField):
    """
    CharField que cifra automáticamente los datos antes de guardarlos
    y los descifra al recuperarlos.

    Usa Fernet (symmetric encryption) de la librería cryptography.
    El max_length se multiplica por 4 internamente para dar espacio al token cifrado.
    """

    description = "Encrypted CharField"

    def __init__(self, *args, **kwargs):
        # El token Fernet es ~4x más largo que el plaintext
        if "max_length" in kwargs:
            kwargs["max_length"] = int(kwargs["max_length"] * 4)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Restaurar el max_length original en la migración
        if "max_length" in kwargs:
            kwargs["max_length"] = int(kwargs["max_length"] / 4)
        return name, path, args, kwargs


class EncryptedTextField(_FernetMixin, models.TextField):
    """
    TextField que cifra automáticamente los datos.
    Usar para textos largos (notas, credenciales JSON, etc.).
    """

    description = "Encrypted TextField"

"""
Custom Encrypted Field for Django

Provides field-level encryption using Fernet (symmetric encryption)
from the cryptography library.

Usage:
    from core.fields import EncryptedCharField

    class MyModel(models.Model):
        sensitive_data = EncryptedCharField(max_length=100)
"""

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)


class EncryptedCharField(models.CharField):
    """
    CharField que cifra automáticamente los datos antes de guardarlos
    y los descifra al recuperarlos.

    Usa Fernet (symmetric encryption) de la librería cryptography.
    """

    description = "Encrypted CharField"

    _cached_fernet = None

    def __init__(self, *args, **kwargs):
        if "max_length" in kwargs:
            kwargs["max_length"] = int(kwargs["max_length"] * 4)

        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        if EncryptedCharField._cached_fernet is None:
            try:
                from cryptography.fernet import Fernet

                encryption_key = getattr(settings, "ENCRYPTION_KEY", None)
                if not encryption_key:
                    raise ImproperlyConfigured(
                        "ENCRYPTION_KEY is required. Generate one with: "
                        'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
                    )
                fernet_key = encryption_key.encode()
                EncryptedCharField._cached_fernet = Fernet(fernet_key)
            except Exception as e:
                logger.error(f"Error inicializando Fernet: {e}")
                raise
        return EncryptedCharField._cached_fernet

    @property
    def fernet(self):
        return self._get_fernet()

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        try:
            if isinstance(value, str) and value.startswith("gAAAAA"):
                return value
            encrypted = self.fernet.encrypt(value.encode())
            return encrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Error cifrando valor: {e}")
            raise ValueError(f"Fallo crítico al cifrar campo sensible: {e}") from e

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            decrypted = self.fernet.decrypt(value.encode())
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error("Error descifrando campo %s (devolviendo marcador): %s", self.name, e)
            return "[cifrado]"

    def to_python(self, value):
        if value is None or value == "":
            return value
        return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "max_length" in kwargs:
            kwargs["max_length"] = int(kwargs["max_length"] / 4)
        return name, path, args, kwargs


class EncryptedTextField(models.TextField):
    """
    TextField que cifra automáticamente los datos.
    Similar a EncryptedCharField pero para textos largos.
    """

    description = "Encrypted TextField"

    _cached_fernet = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        if EncryptedTextField._cached_fernet is None:
            try:
                from cryptography.fernet import Fernet

                encryption_key = getattr(settings, "ENCRYPTION_KEY", None)
                if not encryption_key:
                    raise ImproperlyConfigured(
                        "ENCRYPTION_KEY is required. Generate one with: "
                        'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
                    )
                fernet_key = encryption_key.encode()
                EncryptedTextField._cached_fernet = Fernet(fernet_key)
            except Exception as e:
                logger.error(f"Error inicializando Fernet: {e}")
                raise
        return EncryptedTextField._cached_fernet

    @property
    def fernet(self):
        return self._get_fernet()

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        try:
            if isinstance(value, str) and value.startswith("gAAAAA"):
                return value
            encrypted = self.fernet.encrypt(value.encode())
            return encrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Error cifrando valor: {e}")
            raise ValueError(f"Fallo crítico al cifrar campo sensible: {e}") from e

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            decrypted = self.fernet.decrypt(value.encode())
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error("Error descifrando campo %s (devolviendo marcador): %s", self.name, e)
            return "[cifrado]"

    def to_python(self, value):
        if value is None or value == "":
            return value
        return value

"""
Custom Encrypted Field for Django

Provides field-level encryption using Fernet (symmetric encryption)
from the cryptography library.

Usage:
    from core.fields import EncryptedCharField
    
    class MyModel(models.Model):
        sensitive_data = EncryptedCharField(max_length=100)
"""
import base64
import logging
from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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
        # Aumentar max_length para acomodar datos cifrados
        if 'max_length' in kwargs:
            kwargs['max_length'] = int(kwargs['max_length'] * 4)
        
        super().__init__(*args, **kwargs)
    
    def _get_fernet(self):
        """Obtiene o crea una instancia de Fernet usando caché de clase"""
        if EncryptedCharField._cached_fernet is None:
            try:
                secret_key = settings.SECRET_KEY.encode()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'travelhub_encryption_salt',
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(secret_key))
                EncryptedCharField._cached_fernet = Fernet(key)
            except Exception as e:
                logger.error(f"Error inicializando Fernet: {e}")
                raise
        return EncryptedCharField._cached_fernet

    @property
    def fernet(self):
        return self._get_fernet()

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        try:
            if isinstance(value, str) and value.startswith('gAAAAA'):
                return value
            encrypted = self.fernet.encrypt(value.encode())
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Error cifrando valor: {e}")
            return value

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        try:
            decrypted = self.fernet.decrypt(value.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.warning(f"No se pudo descifrar valor, retornando como texto plano: {e}")
            return value
    
    def to_python(self, value):
        """
        Convierte el valor a Python (usado en formularios)
        """
        if value is None or value == '':
            return value
        
        # Si viene de la DB, ya está descifrado por from_db_value
        # Si viene de un formulario, es texto plano
        return value
    
    def deconstruct(self):
        """
        Para migraciones de Django
        """
        name, path, args, kwargs = super().deconstruct()
        # Restaurar max_length original
        if 'max_length' in kwargs:
            kwargs['max_length'] = int(kwargs['max_length'] / 4)
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
        """Obtiene o crea una instancia de Fernet usando caché de clase"""
        if EncryptedTextField._cached_fernet is None:
            try:
                secret_key = settings.SECRET_KEY.encode()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'travelhub_encryption_salt',
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(secret_key))
                EncryptedTextField._cached_fernet = Fernet(key)
            except Exception as e:
                logger.error(f"Error inicializando Fernet: {e}")
                raise
        return EncryptedTextField._cached_fernet

    @property
    def fernet(self):
        return self._get_fernet()

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        try:
            if isinstance(value, str) and value.startswith('gAAAAA'):
                return value
            encrypted = self.fernet.encrypt(value.encode())
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Error cifrando valor: {e}")
            return value

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        try:
            decrypted = self.fernet.decrypt(value.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.warning(f"No se pudo descifrar valor, retornando como texto plano: {e}")
            return value
    
    def to_python(self, value):
        """Convierte el valor a Python"""
        if value is None or value == '':
            return value
        return value

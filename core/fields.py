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
    
    def __init__(self, *args, **kwargs):
        # Aumentar max_length para acomodar datos cifrados
        # Los datos cifrados Fernet son significativamente más grandes que el original
        if 'max_length' in kwargs:
            kwargs['max_length'] = int(kwargs['max_length'] * 4)
        
        super().__init__(*args, **kwargs)
        self._fernet = self._get_fernet()
    
    def _get_fernet(self):
        """Obtiene instancia de Fernet usando SECRET_KEY de Django"""
        try:
            # Usar SECRET_KEY de Django como base para la clave de cifrado
            secret_key = settings.SECRET_KEY.encode()
            
            # Derivar una clave de 32 bytes usando PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'travelhub_encryption_salt',  # Salt fijo para consistencia
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key))
            
            return Fernet(key)
        except Exception as e:
            logger.error(f"Error inicializando Fernet: {e}")
            raise
    
    def get_prep_value(self, value):
        """
        Cifra el valor antes de guardarlo en la base de datos
        """
        if value is None or value == '':
            return value
        
        try:
            # Si ya está cifrado (empieza con 'gAAAAA'), no volver a cifrar
            if isinstance(value, str) and value.startswith('gAAAAA'):
                return value
            
            # Cifrar el valor
            encrypted = self._fernet.encrypt(value.encode())
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Error cifrando valor: {e}")
            # En caso de error, guardar sin cifrar (mejor que perder el dato)
            return value
    
    def from_db_value(self, value, expression, connection):
        """
        Descifra el valor al recuperarlo de la base de datos
        """
        if value is None or value == '':
            return value
        
        try:
            # Intentar descifrar
            decrypted = self._fernet.decrypt(value.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            # Si no se puede descifrar, probablemente es texto plano
            # (datos existentes antes de la migración)
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = self._get_fernet()
    
    def _get_fernet(self):
        """Obtiene instancia de Fernet usando SECRET_KEY de Django"""
        try:
            secret_key = settings.SECRET_KEY.encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'travelhub_encryption_salt',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key))
            return Fernet(key)
        except Exception as e:
            logger.error(f"Error inicializando Fernet: {e}")
            raise
    
    def get_prep_value(self, value):
        """Cifra el valor antes de guardarlo"""
        if value is None or value == '':
            return value
        
        try:
            if isinstance(value, str) and value.startswith('gAAAAA'):
                return value
            
            encrypted = self._fernet.encrypt(value.encode())
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Error cifrando valor: {e}")
            return value
    
    def from_db_value(self, value, expression, connection):
        """Descifra el valor al recuperarlo"""
        if value is None or value == '':
            return value
        
        try:
            decrypted = self._fernet.decrypt(value.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.warning(f"No se pudo descifrar valor, retornando como texto plano: {e}")
            return value
    
    def to_python(self, value):
        """Convierte el valor a Python"""
        if value is None or value == '':
            return value
        return value

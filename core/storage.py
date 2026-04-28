# core/storage.py
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from cloudinary_storage.storage import RawMediaCloudinaryStorage

# Check if Cloudinary is enabled in settings safely
use_cloudinary = getattr(settings, 'USE_CLOUDINARY', False)

if use_cloudinary:
    class RawFileStorage(RawMediaCloudinaryStorage):
        """Storage para archivos raw (PDF, TXT, EML) en Cloudinary"""
        
        def _prepend_prefix(self, name):
            """No agregar prefijo 'media/' - usar path directo"""
            return name
else:
    class RawFileStorage(FileSystemStorage):
        """Storage local (cuando Cloudinary está desactivado o la clave es inválida)"""
        pass

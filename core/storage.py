# core/storage.py
from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Estrategia de Storage Dinámica (Fase 3: Unificación Cloudflare R2)
use_r2 = getattr(settings, 'USE_R2', False)
use_cloudinary = getattr(settings, 'USE_CLOUDINARY', False)

if use_r2:
    # ☁️ CLOUDFLARE R2 (S3 Compatible)
    from storages.backends.s3 import S3Storage
    class RawFileStorage(S3Storage):
        """Storage para archivos raw (PDF, TXT, EML) en Cloudflare R2"""
        pass
        
elif use_cloudinary:
    from cloudinary_storage.storage import RawMediaCloudinaryStorage
    class RawFileStorage(RawMediaCloudinaryStorage):
        """Storage para archivos raw (PDF, TXT, EML) en Cloudinary"""
        
        def _prepend_prefix(self, name):
            """No agregar prefijo 'media/' - usar path directo"""
            return name
else:
    class RawFileStorage(FileSystemStorage):
        """Storage local (Desarrollo o Fallback)"""
        pass

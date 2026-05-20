# core/storage.py
from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Estrategia de Storage Dinámica (Fase 3: Unificación Cloudflare R2)
use_r2 = getattr(settings, 'USE_R2', False)

if use_r2:
    # ☁️ CLOUDFLARE R2 (S3 Compatible)
    import os
    from storages.backends.s3boto3 import S3Boto3Storage

    class RawFileStorage(S3Boto3Storage):
        """Storage para archivos raw (PDF, TXT, EML) en Cloudflare R2"""
        def __init__(self, **kwargs):
            kwargs.setdefault('access_key', os.getenv("R2_ACCESS_KEY_ID"))
            kwargs.setdefault('secret_key', os.getenv("R2_SECRET_ACCESS_KEY"))
            kwargs.setdefault('bucket_name', os.getenv("R2_BUCKET_NAME"))
            kwargs.setdefault('endpoint_url', os.getenv("R2_ENDPOINT_URL"))
            kwargs.setdefault('region_name', "auto")
            kwargs.setdefault('file_overwrite', False)
            # 🔒 Seguridad SaaS: No permitir acceso público, requerir URLs firmadas
            kwargs.setdefault('default_acl', 'private')
            kwargs.setdefault('querystring_auth', True)
            kwargs.setdefault('querystring_expire', 3600) # 1 hora
            super().__init__(**kwargs)
        
else:
    class RawFileStorage(FileSystemStorage):
        """Storage local (Desarrollo o Fallback)"""
        pass

# core/storage.py
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

# Dinámicamente heredamos del storage configurado
use_r2 = getattr(settings, "USE_R2", True)

# Dominio custom de R2 (ej: static.travelhub.cc)
# Si está configurado, las URLs son públicas y permanentes (no pre-signed).
_r2_custom_domain = os.getenv("AWS_S3_CUSTOM_DOMAIN")

if use_r2:

    class RawFileStorage(S3Boto3Storage):
        """
        Storage para archivos raw (PDF, TXT, EML) en Cloudflare R2.

        Estrategia de URL:
        - Si hay dominio custom (AWS_S3_CUSTOM_DOMAIN): URLs públicas y permanentes.
          Requiere que el bucket tenga acceso público o Cloudflare Transform Rules.
        - Si NO hay dominio custom: URLs pre-signed con expiración de 7 días.
          (Suficiente para uso operativo sin que el usuario vea URLs expiradas.)
        """

        def __init__(self, **kwargs):
            kwargs.setdefault("access_key", os.getenv("R2_ACCESS_KEY_ID"))
            kwargs.setdefault("secret_key", os.getenv("R2_SECRET_ACCESS_KEY"))
            kwargs.setdefault("bucket_name", os.getenv("R2_BUCKET_NAME"))
            kwargs.setdefault("endpoint_url", os.getenv("R2_ENDPOINT_URL"))
            kwargs.setdefault("region_name", "auto")
            kwargs.setdefault("file_overwrite", False)
            kwargs.setdefault("default_acl", "private")

            if _r2_custom_domain:
                # Con dominio custom → URLs permanentes (sin firma)
                kwargs.setdefault("custom_domain", _r2_custom_domain)
                kwargs.setdefault("querystring_auth", False)
            else:
                # Sin dominio custom → pre-signed URLs con expiración larga (7 días)
                kwargs.setdefault("querystring_auth", True)
                kwargs.setdefault("querystring_expire", 60 * 60 * 24 * 7)  # 7 días

            super().__init__(**kwargs)

else:

    class RawFileStorage(FileSystemStorage):
        """Storage para archivos raw en Local Filesystem para desarrollo/pruebas"""

        pass

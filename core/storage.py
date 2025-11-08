# core/storage.py
from cloudinary_storage.storage import RawMediaCloudinaryStorage

class RawFileStorage(RawMediaCloudinaryStorage):
    """Storage para archivos raw (PDF, TXT, EML) en Cloudinary"""
    pass

# core/storage.py
from cloudinary_storage.storage import RawMediaCloudinaryStorage

class RawFileStorage(RawMediaCloudinaryStorage):
    """Storage para archivos raw (PDF, TXT, EML) en Cloudinary"""
    
    def url(self, name):
        """Generar URL pública para archivos raw"""
        if not name:
            return ''
        return super().url(name)

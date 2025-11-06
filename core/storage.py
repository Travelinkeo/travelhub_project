"""
Storage personalizado para Cloudinary que maneja PDFs y otros archivos no-imagen
"""
from cloudinary_storage.storage import RawMediaCloudinaryStorage


class PDFCloudinaryStorage(RawMediaCloudinaryStorage):
    """
    Storage para PDFs y archivos raw en Cloudinary.
    Usa resource_type='raw' en lugar de 'image'.
    """
    pass

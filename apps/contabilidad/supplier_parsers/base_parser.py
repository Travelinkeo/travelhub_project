from abc import ABC, abstractmethod
from typing import Any


class BaseSupplierReportParser(ABC):
    """
    Clase base abstracta para parsers de reportes de ventas de proveedores.
    Cada proveedor (CTG, MY DESTINY, etc.) implementa su propia estrategia.
    """

    def __init__(self, pdf_bytes: bytes, filename: str = "", subject: str = ""):
        """__init__."""
        self.pdf_bytes = pdf_bytes
        self.filename = filename
        self.subject = subject

    @abstractmethod
    def parse(self) -> dict[str, Any]:
        """
        Parsea el PDF y retorna una estructura estándar con encabezado e items.
        """
        pass

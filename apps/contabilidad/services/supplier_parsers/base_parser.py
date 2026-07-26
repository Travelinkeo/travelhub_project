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
        Parsea el PDF y retorna una estructura estándar con encabezado e items:
        {
            "proveedor_nombre": "CTG",
            "codigo_agencia_proveedor": "7842",
            "fecha_reporte_desde": "2026-03-02",
            "fecha_reporte_hasta": "2026-03-08",
            "saldo_anterior": Decimal("1655.78"),
            "monto_total_ventas": Decimal("1065.17"),
            "saldo_final": Decimal("-590.61"),
            "items": [...]
        }
        """
        pass

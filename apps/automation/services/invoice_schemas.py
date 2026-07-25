"""Servicio de invoice schemas para la aplicación automation.
"""

from pydantic import BaseModel, Field


class InvoiceDataSchema(BaseModel):
    """Esquema para la extracción de datos de facturas de proveedores."""

    proveedor_nombre: str = Field(description="Nombre o Razón Social del proveedor/aerolínea")
    numero_factura: str = Field(description="Número de factura o referencia de liquidación")
    monto_total: float = Field(description="Monto total a pagar (neto + impuestos)")
    moneda_iso: str = Field(description="Código ISO de la moneda (USD, EUR, BSD, etc.)")
    fecha_emision: str = Field(description="Fecha de emisión en formato YYYY-MM-DD")
    detalles: list[str] = Field(
        default=[], description="Lista breve de conceptos o servicios incluidos"
    )

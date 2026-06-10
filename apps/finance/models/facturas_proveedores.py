from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin, SoftDeleteModel


class FacturaProveedor(AgenciaMixin, SoftDeleteModel, models.Model):
    """
    Modelo para registrar facturas recibidas de proveedores vía email.
    Estas facturas quedan pendientes de conciliación contra los pagos o ventas del sistema.
    """

    class EstadoFactura(models.TextChoices):
        PENDIENTE_CONCILIACION = "PEN_CON", _("Pendiente de Conciliación")
        CONCILIADA = "CONCILIADA", _("Conciliada")
        RECHAZADA = "RECHAZADA", _("Rechazada")
        REQUIERE_REVISION = "REV_MAN", _("Requiere Revisión Manual")

    id_factura_proveedor = models.AutoField(primary_key=True)

    # Datos extraídos por IA
    proveedor_nombre = models.CharField(_("Proveedor (Texto)"), max_length=255)
    proveedor = models.ForeignKey(
        "bookings.Proveedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facturas_proveedor_registradas",
    )
    numero_factura = models.CharField(_("Número de Factura"), max_length=100)
    monto_total = models.DecimalField(_("Monto Total"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey("common.Moneda", on_delete=models.PROTECT, verbose_name=_("Moneda"))
    fecha_emision = models.DateField(_("Fecha de Emisión"))

    # Control de estado y auditoría
    estado = models.CharField(
        max_length=20, choices=EstadoFactura.choices, default=EstadoFactura.PENDIENTE_CONCILIACION
    )
    raw_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Hash SHA-256 del contenido para evitar duplicidad"),
    )
    archivo_pdf = models.FileField(upload_to="facturas_proveedores/%Y/%m/", blank=True, null=True)
    datos_json = models.JSONField(
        default=dict, blank=True, help_text=_("Estructura completa extraída por IA")
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Factura de Proveedor")
        verbose_name_plural = _("Facturas de Proveedores")
        ordering = ["-fecha_registro"]
        indexes = [
            models.Index(fields=["agencia", "estado"]),
            models.Index(fields=["raw_hash"]),
        ]

    def __str__(self):
        return f"{self.proveedor_nombre} - {self.numero_factura} ({self.monto_total} {self.moneda.codigo_iso})"

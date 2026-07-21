from django.db import models, transaction

from apps.common.models import Moneda  # noqa: F401 re-export for backwards compatibility
from core.models.base import AgenciaMixin


def generar_numero_factura_atomico(model_cls, fecha_emision, prefix=""):
    """
    Genera un número de factura correlativo atómico y libre de condiciones de carrera.
    """
    if not prefix:
        prefix = f"F-{fecha_emision.strftime('%Y%m%d')}"

    with transaction.atomic():
        field_name = "numero_factura" if hasattr(model_cls, "numero_factura") else "numero_control"
        last_obj = (
            model_cls.objects.select_for_update()
            .filter(**{f"{field_name}__startswith": prefix})
            .order_by(f"-{field_name}")
            .first()
        )
        if last_obj:
            val = getattr(last_obj, field_name, "")
            try:
                seq = int(val.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}-{seq:04d}"


# Stubs for migration & apps.get_model compatibility


class TasaCambioBCV(models.Model):
    fecha = models.DateField(unique=True, db_index=True)
    tasa = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    class Meta:
        verbose_name = "Tasa de Cambio BCV"
        verbose_name_plural = "Tasas de Cambio BCV"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha}: {self.tasa} VES/USD"


class ConfiguracionFiscal(AgenciaMixin, models.Model):
    iva_por_defecto = models.DecimalField(max_digits=15, decimal_places=4, default=16.0000)
    igtf_por_defecto = models.DecimalField(max_digits=15, decimal_places=4, default=3.0000)
    es_contribuyente_especial = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuración Fiscal"
        verbose_name_plural = "Configuraciones Fiscales"

    def __str__(self):
        return f"ConfigFiscal #{self.agencia_id} — IVA={self.iva_por_defecto}%"


class Factura(AgenciaMixin, models.Model):
    cliente = models.ForeignKey(
        "crm.Cliente",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    fecha_emision = models.DateField(null=True, blank=True)
    numero_control = models.CharField(max_length=50, unique=True)

    tasa_bcv_aplicada = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    subtotal_usd = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    subtotal_ves = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    total_iva_usd = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    total_iva_ves = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    total_igtf_usd = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    total_igtf_ves = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    gran_total_usd = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    gran_total_ves = models.DecimalField(max_digits=15, decimal_places=4, default=0)

    class EstadoFactura(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        EMITIDA = "EMITIDA", "Emitida"
        ANULADA = "ANULADA", "Anulada"

    estado = models.CharField(
        max_length=10,
        choices=EstadoFactura.choices,
        default=EstadoFactura.BORRADOR,
    )

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"Factura #{self.numero_control}"


class ItemFactura(AgenciaMixin, models.Model):
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name="items",
    )
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=15, decimal_places=4, default=1)
    precio_unitario_usd = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    exento = models.BooleanField(default=False)
    total_linea_usd = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    class Meta:
        verbose_name = "Item de Factura"
        verbose_name_plural = "Items de Factura"

    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"


class Pago(AgenciaMixin, models.Model):
    factura = models.ForeignKey(
        Factura,
        on_delete=models.PROTECT,
        related_name="pagos",
        null=True,
        blank=True,
    )
    monto_usd = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    monto_ves = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    metodo_pago = models.CharField(max_length=50, null=True, blank=True)
    referencia = models.CharField(max_length=100, blank=True, default="")
    fecha_pago = models.DateField()

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha_pago"]

    def __str__(self):
        return f"Pago {self.referencia or self.pk} — {self.monto_usd} USD / {self.monto_ves} VES"

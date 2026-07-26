from decimal import Decimal

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
    """TasaCambioBCV."""

    fecha = models.DateField(unique=True, db_index=True)
    tasa = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    class Meta:
        verbose_name = "Tasa de Cambio BCV"
        verbose_name_plural = "Tasas de Cambio BCV"
        ordering = ["-fecha"]

    def __str__(self):
        """__str__."""
        return f"{self.fecha}: {self.tasa} VES/USD"


class ConfiguracionFiscal(AgenciaMixin, models.Model):
    """ConfiguracionFiscal."""

    PAISES = [
        ("VEN", "Venezuela"),
        ("COL", "Colombia"),
        ("MEX", "México"),
    ]

    pais = models.CharField(max_length=3, choices=PAISES, default="VEN")
    iva_por_defecto = models.DecimalField(max_digits=15, decimal_places=4, default=16.0000)
    igtf_por_defecto = models.DecimalField(max_digits=15, decimal_places=4, default=3.0000)
    es_contribuyente_especial = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuración Fiscal"
        verbose_name_plural = "Configuraciones Fiscales"

    def __str__(self):
        """__str__."""
        return f"ConfigFiscal #{self.agencia_id} — IVA={self.iva_por_defecto}%"


class Factura(AgenciaMixin, models.Model):
    """Factura."""

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
        """EstadoFactura."""

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
        """__str__."""
        return f"Factura #{self.numero_control}"


class ItemFactura(AgenciaMixin, models.Model):
    """ItemFactura."""

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
        """__str__."""
        return f"{self.descripcion} x {self.cantidad}"


class Pago(AgenciaMixin, models.Model):
    """Pago."""

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
        """__str__."""
        return f"Pago {self.referencia or self.pk} — {self.monto_usd} USD / {self.monto_ves} VES"


# ─────────────────────────────────────────────────────────────────
# MODELOS FINANCIEROS OPERATIVOS — con tabla real en PostgreSQL
# Anteriormente eran stubs managed=False en models_stubs.py.
# Migrados a modelos reales para garantizar persistencia de datos.
# ─────────────────────────────────────────────────────────────────


class GastoOperativo(AgenciaMixin, models.Model):
    """
    Registro de gastos operativos de la agencia.

    Cubre: alquiler, servicios, sueldos administrativos, publicidad y
    cualquier gasto no asociado directamente a una venta de cliente.
    Cada registro se aísla por agencia (multi-tenant vía AgenciaMixin).
    """

    class CategoriaGasto(models.TextChoices):
        """CategoriaGasto."""

        ALQUILER = "ALQ", "Alquiler de Oficina"
        SERVICIOS = "SER", "Servicios (Luz/Agua/Internet)"
        NOMINA = "NOM", "Nómina y Sueldos"
        PUBLICIDAD = "PUB", "Publicidad y Marketing"
        TRANSPORTE = "TRA", "Transporte y Viáticos"
        TECNOLOGIA = "TEC", "Tecnología y Software"
        OTROS = "OTR", "Otros Gastos"

    class EstadoContable(models.TextChoices):
        """EstadoContable."""

        PENDIENTE = "PEN", "Pendiente de Contabilizar"
        CONTABILIZADO = "CON", "Contabilizado"
        ERROR = "ERR", "Error en Contabilización"

    descripcion = models.CharField(max_length=255, verbose_name="Descripción")
    monto = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    moneda = models.ForeignKey(
        "common.Moneda",
        on_delete=models.PROTECT,
        verbose_name="Moneda",
    )
    tasa_bcv = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Tasa BCV al registro",
        help_text="Tasa USD/VES del BCV en la fecha del gasto. Se llena automáticamente.",
    )
    fecha = models.DateField(verbose_name="Fecha del Gasto")
    categoria = models.CharField(
        max_length=3,
        choices=CategoriaGasto.choices,
        default=CategoriaGasto.OTROS,
        verbose_name="Categoría",
    )
    comprobante = models.FileField(
        upload_to="gastos/comprobantes/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="Comprobante",
    )
    notas = models.TextField(blank=True, default="", verbose_name="Notas")
    estado_contable = models.CharField(
        max_length=3,
        choices=EstadoContable.choices,
        default=EstadoContable.PENDIENTE,
        verbose_name="Estado Contable",
    )
    error_contable_msg = models.TextField(
        blank=True,
        null=True,
        verbose_name="Mensaje de Error Contable",
    )
    creado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Registrado por",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gasto Operativo"
        verbose_name_plural = "Gastos Operativos"
        ordering = ["-fecha", "-creado"]
        indexes = [
            models.Index(fields=["agencia", "fecha"]),
            models.Index(fields=["agencia", "categoria"]),
            models.Index(fields=["agencia", "estado_contable"]),
        ]

    def __str__(self):
        """__str__."""
        return f"{self.descripcion} — {self.monto} ({self.fecha})"

    @property
    def monto_bs(self):
        """Monto convertido a bolívares usando la tasa BCV registrada."""
        if self.tasa_bcv and self.moneda and getattr(self.moneda, "codigo_iso", "") == "USD":
            return (self.monto * self.tasa_bcv).quantize(Decimal("0.01"))
        return None


class FacturaConsolidada(AgenciaMixin, models.Model):
    """
    Factura fiscal VEN-NIF con doble moneda USD/VES.

    Gestiona la facturación conforme a la normativa venezolana:
    IVA 16% (general) e IVA 25% (suntuario/turismo), IGTF 3%,
    y doble registro en USD y bolívares a tasa BCV oficial.

    Una FacturaConsolidada puede agrupar múltiples ventas de la agencia
    en un mismo documento fiscal.
    """

    class EstadoFactura(models.TextChoices):
        """EstadoFactura."""

        BORRADOR = "BOR", "Borrador"
        EMITIDA = "EMI", "Emitida"
        PAGADA = "PAG", "Pagada"
        ANULADA = "ANU", "Anulada"

    class TipoOperacion(models.TextChoices):
        """TipoOperacion."""

        VENTA_PROPIA = "VP", "Venta Propia"
        INTERMEDIACION = "IN", "Intermediación"

    # Identificación fiscal
    numero_factura = models.CharField(max_length=50, unique=True, verbose_name="Número de Factura")
    numero_control = models.CharField(
        max_length=50, blank=True, default="", verbose_name="Número de Control"
    )
    fecha_emision = models.DateField(verbose_name="Fecha de Emisión")

    # Datos del cliente (receptor)
    cliente = models.ForeignKey(
        "crm.Cliente",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Cliente",
    )
    cliente_rif = models.CharField(
        max_length=20, blank=True, default="", verbose_name="RIF del Cliente"
    )
    cliente_razon_social = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Razón Social del Cliente"
    )
    cliente_es_residente = models.BooleanField(
        default=True, verbose_name="Cliente es Residente en Venezuela"
    )

    # Tipo de operación
    tipo_operacion = models.CharField(
        max_length=2,
        choices=TipoOperacion.choices,
        default=TipoOperacion.VENTA_PROPIA,
        verbose_name="Tipo de Operación",
    )

    # Montos base (USD)
    subtotal_base_gravada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Base Gravada (USD)",
    )
    subtotal_exento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Monto Exento (USD)",
    )
    monto_iva_16 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="IVA 16% (USD)",
    )
    monto_iva_adicional = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="IVA Adicional 25% suntuario (USD)",
    )
    monto_igtf = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="IGTF 3% (USD)",
    )
    gran_total_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Total General (USD)",
    )

    # Equivalente en bolívares
    tasa_cambio_bcv = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Tasa BCV aplicada",
    )
    gran_total_ves = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Total General (VES)",
    )

    # Configuración fiscal de la agencia
    es_contribuyente_especial = models.BooleanField(
        default=False,
        verbose_name="Agencia es Contribuyente Especial (aplica IGTF)",
    )

    # Estado y archivo
    estado = models.CharField(
        max_length=3,
        choices=EstadoFactura.choices,
        default=EstadoFactura.BORRADOR,
        verbose_name="Estado",
        db_index=True,
    )
    archivo_pdf = models.FileField(
        upload_to="facturas/pdfs/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="PDF de Factura",
    )
    notas = models.TextField(blank=True, default="", verbose_name="Notas")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Factura Consolidada VEN-NIF"
        verbose_name_plural = "Facturas Consolidadas VEN-NIF"
        ordering = ["-fecha_emision", "-creado"]
        indexes = [
            models.Index(fields=["agencia", "estado"]),
            models.Index(fields=["agencia", "fecha_emision"]),
            models.Index(fields=["numero_factura"]),
        ]

    def __str__(self):
        """__str__."""
        return f"FC-{self.numero_factura} | {self.gran_total_usd} USD ({self.estado})"

    def calcular_totales(self):
        """
        Recalcula todos los totales a partir de los ítems.
        Aplica lógica fiscal venezolana: IVA 16% sobre base gravada,
        IGTF 3% si la agencia es contribuyente especial.
        """
        base_gravada = Decimal("0.00")
        exento = Decimal("0.00")
        iva_16 = Decimal("0.00")

        for item in self.items_consolidados.all():
            if item.exento:
                exento += item.subtotal.quantize(Decimal("0.01"))
            else:
                base_gravada += item.subtotal.quantize(Decimal("0.01"))
                iva_16 += (item.subtotal * item.alicuota_iva / Decimal("100")).quantize(
                    Decimal("0.01")
                )

        self.subtotal_base_gravada = base_gravada
        self.subtotal_exento = exento
        self.monto_iva_16 = iva_16

        if self.es_contribuyente_especial:
            self.monto_igtf = ((base_gravada + iva_16) * Decimal("0.03")).quantize(Decimal("0.01"))
        else:
            self.monto_igtf = Decimal("0.00")

        self.gran_total_usd = (base_gravada + exento + iva_16 + self.monto_igtf).quantize(
            Decimal("0.01")
        )

        if self.tasa_cambio_bcv:
            self.gran_total_ves = (self.gran_total_usd * self.tasa_cambio_bcv).quantize(
                Decimal("0.01")
            )


class ItemFacturaConsolidada(AgenciaMixin, models.Model):
    """Línea de ítem dentro de una FacturaConsolidada."""

    class TipoServicio(models.TextChoices):
        """TipoServicio."""

        AEREO_INTERNACIONAL = "TAI", "Transporte Aéreo Internacional"
        AEREO_NACIONAL = "TAN", "Transporte Aéreo Nacional"
        HOTEL = "HOT", "Alojamiento"
        PAQUETE = "PAQ", "Paquete Turístico"
        SEGURO = "SEG", "Seguro de Viaje"
        TRASLADO = "TRA", "Traslado"
        OTROS = "OTR", "Otros Servicios"

    factura = models.ForeignKey(
        FacturaConsolidada,
        on_delete=models.CASCADE,
        related_name="items_consolidados",
        verbose_name="Factura",
    )
    descripcion = models.CharField(max_length=500, verbose_name="Descripción")
    tipo_servicio = models.CharField(
        max_length=3,
        choices=TipoServicio.choices,
        default=TipoServicio.OTROS,
        verbose_name="Tipo de Servicio",
    )
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        verbose_name="Cantidad",
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Precio Unitario (USD)",
    )
    exento = models.BooleanField(
        default=False,
        verbose_name="Exento de IVA",
        help_text="Ej: transporte internacional exento conforme a Ley IVA art. 16",
    )
    alicuota_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("16.00"),
        verbose_name="Alícuota IVA %",
    )
    # Referencia al boleto si aplica
    numero_boleto = models.CharField(max_length=50, blank=True, default="")
    nombre_pasajero = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        verbose_name = "Ítem de Factura Consolidada"
        verbose_name_plural = "Ítems de Factura Consolidada"

    def __str__(self):
        """__str__."""
        return f"{self.descripcion} x {self.cantidad}"

    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario).quantize(Decimal("0.01"))


class RetencionISLR(AgenciaMixin, models.Model):
    """
    Retención de Impuesto Sobre La Renta (ISLR) sobre comisiones y honorarios.

    Conforme a la normativa venezolana, las agencias deben retener el 5% sobre
    comisiones mercantiles pagadas a agentes y freelancers, y emitir el
    comprobante de retención correspondiente.
    """

    class TipoOperacion(models.TextChoices):
        """TipoOperacion."""

        COMISIONES_MERCANTILES = "CM", "Comisiones Mercantiles (5%)"
        HONORARIOS_PROFESIONALES = "HP", "Honorarios Profesionales (3%)"
        ARRENDAMIENTO = "AR", "Arrendamiento (3%)"
        OTROS = "OT", "Otros"

    class Estado(models.TextChoices):
        """Estado."""

        PENDIENTE = "PEN", "Pendiente"
        APLICADA = "APL", "Aplicada"
        ANULADA = "ANU", "Anulada"

    # Identificación del comprobante
    numero_comprobante = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número de Comprobante de Retención",
    )
    fecha_emision = models.DateField(verbose_name="Fecha de Emisión")
    periodo_fiscal = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        verbose_name="Período Fiscal (YYYY-MM)",
        help_text="Se genera automáticamente de la fecha de emisión",
    )

    # Tipo de operación
    tipo_operacion = models.CharField(
        max_length=2,
        choices=TipoOperacion.choices,
        default=TipoOperacion.COMISIONES_MERCANTILES,
        verbose_name="Tipo de Operación",
    )

    # Sujeto retenido
    retenido_rif = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="RIF del Sujeto Retenido",
    )
    retenido_nombre = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Nombre / Razón Social del Retenido",
    )

    # Montos
    base_imponible = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Base Imponible (USD)",
    )
    porcentaje_retencion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
        verbose_name="Porcentaje de Retención %",
    )
    monto_retenido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Retenido (USD)",
        help_text="Se calcula automáticamente al guardar",
    )

    # Relaciones opcionales
    factura = models.ForeignKey(
        FacturaConsolidada,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retenciones_islr",
        verbose_name="Factura Asociada",
    )

    # Estado y soporte
    estado = models.CharField(
        max_length=3,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        verbose_name="Estado",
        db_index=True,
    )
    archivo_comprobante = models.FileField(
        upload_to="retenciones/comprobantes/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="Comprobante PDF",
    )
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Retención ISLR"
        verbose_name_plural = "Retenciones ISLR"
        ordering = ["-fecha_emision"]
        indexes = [
            models.Index(fields=["agencia", "estado"]),
            models.Index(fields=["agencia", "fecha_emision"]),
        ]

    def __str__(self):
        """__str__."""
        return f"ISLR {self.numero_comprobante} — {self.monto_retenido} USD ({self.estado})"

    def save(self, *args, **kwargs):
        """save."""
        # Calcular monto retenido automáticamente
        if self.base_imponible is not None and self.porcentaje_retencion:
            self.monto_retenido = (
                self.base_imponible * self.porcentaje_retencion / Decimal("100")
            ).quantize(Decimal("0.01"))
        # Auto-generar período fiscal
        if self.fecha_emision and not self.periodo_fiscal:
            self.periodo_fiscal = self.fecha_emision.strftime("%Y-%m")
        super().save(*args, **kwargs)

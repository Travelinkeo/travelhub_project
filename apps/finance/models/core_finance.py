import logging
import uuid
import warnings
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin, SoftDeleteModel

# REFACTOR: Nuevos imports
# from apps.crm.models import Cliente # REFACTOR: Usar string 'crm.Cliente'
# from apps.bookings.models import Venta # Circular dependency risk if not careful, use string 'bookings.Venta' or lazy import
from .currencies import Moneda

# REFACTOR: Usar referencias lazy ('contabilidad.AsientoContable') para evitar circulares

logger = logging.getLogger(__name__)


def generar_numero_factura_atomico(model_class, fecha_emision, prefix=None):
    """
    Genera un número de factura secuencial de forma atómica.
    Usa select_for_update() para evitar condiciones de carrera.

    Args:
        model_class: La clase del modelo (Factura o FacturaConsolidada)
        fecha_emision: Date con la fecha de emisión
        prefix: Prefijo opcional (default: F-YYYYMMDD)

    Returns:
        str: Número de factura único (ej: F-20260608-0001)
    """
    if prefix is None:
        prefix = f"F-{fecha_emision.strftime('%Y%m%d')}"

    with transaction.atomic():
        # Obtener el último número de factura del día con lock
        ultimo = (
            model_class.objects.select_for_update()
            .filter(numero_factura__startswith=prefix)
            .order_by("-numero_factura")
            .first()
        )

        if ultimo:
            # Extraer el sufijo numérico y sumar 1
            try:
                sufijo = int(ultimo.numero_factura.split("-")[-1])
                nuevo_sufijo = sufijo + 1
            except (ValueError, IndexError):
                nuevo_sufijo = 1
        else:
            nuevo_sufijo = 1

        return f"{prefix}-{nuevo_sufijo:04d}"


class Factura(AgenciaMixin, SoftDeleteModel, models.Model):
    id_factura = models.AutoField(primary_key=True, verbose_name=_("ID Factura"))
    numero_factura = models.CharField(
        _("Número de Factura"),
        max_length=50,
        unique=True,
        blank=True,
        help_text=_("Puede ser un correlativo fiscal o interno."),
    )

    venta_asociada_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("ID Venta Asociada"),
    )

    @property
    def venta_asociada(self):
        if not self.venta_asociada_id:
            return None
        from apps.bookings.models import Venta

        return Venta.objects.filter(pk=self.venta_asociada_id).first()

    @venta_asociada.setter
    def venta_asociada(self, value):
        self.venta_asociada_id = value.pk if value else None

    # agencia la provee AgenciaMixin
    cliente = models.ForeignKey(
        "crm.Cliente", on_delete=models.PROTECT, verbose_name=_("Cliente"), blank=True, null=True
    )

    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    monto_impuestos = models.DecimalField(
        _("Monto Impuestos"), max_digits=12, decimal_places=2, default=0
    )
    monto_total = models.DecimalField(
        _("Monto Total"), max_digits=12, decimal_places=2, editable=False, default=0
    )
    saldo_pendiente = models.DecimalField(
        _("Saldo Pendiente"), max_digits=12, decimal_places=2, editable=False, default=0
    )

    class TipoFactura(models.TextChoices):
        PROPIA = "PRO", _("Factura Propia (Comisión/Servicios)")
        TERCEROS = "TER", _("Factura por Cuenta de Terceros (Boletos)")
        NOTA_DEBITO = "ND", _("Nota de Débito")
        NOTA_CREDITO = "NC", _("Nota de Crédito")

    tipo_factura = models.CharField(
        _("Tipo de Factura"), max_length=3, choices=TipoFactura.choices, default=TipoFactura.PROPIA
    )
    numero_control = models.CharField(
        _("Número de Control"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Número de Control Fiscal obligatorio."),
    )

    # Snapshot de cliente (para historico fiscal)
    cliente_nombre = models.CharField(_("Nombre/Razón Social Cliente"), max_length=255, blank=True)
    cliente_rif = models.CharField(_("RIF/Documento Cliente"), max_length=20, blank=True)
    cliente_direccion = models.TextField(_("Dirección Fiscal Cliente"), blank=True)
    cliente_telefono = models.CharField(_("Teléfono Cliente"), max_length=50, blank=True)

    # Convertibilidad (Multimoneda)
    tasa_cambio = models.DecimalField(
        _("Tasa de Cambio (BCV)"),
        max_digits=12,
        decimal_places=4,
        default=1,
        help_text=_("Tasa de cambio vigente a la fecha de emisión."),
    )
    moneda_transaccion = models.CharField(
        _("Moneda Transacción"), max_length=3, default="USD", help_text="Moneda en la que se pagó"
    )

    # Totales Desglosados
    base_imponible = models.DecimalField(
        _("Base Imponible (Gravada)"), max_digits=12, decimal_places=2, default=0
    )
    base_exenta = models.DecimalField(_("Base Exenta"), max_digits=12, decimal_places=2, default=0)

    iva_porcentaje = models.DecimalField(_("% IVA"), max_digits=5, decimal_places=2, default=25)
    iva_monto = models.DecimalField(_("Monto IVA"), max_digits=12, decimal_places=2, default=0)

    igtf_porcentaje = models.DecimalField(_("% IGTF"), max_digits=5, decimal_places=2, default=3)
    igtf_monto = models.DecimalField(
        _("Monto IGTF"),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Impuesto a Grandes Transacciones Financieras (si aplica)."),
    )

    inatur_porcentaje = models.DecimalField(
        _("% INATUR"), max_digits=5, decimal_places=2, default=1
    )
    inatur_monto = models.DecimalField(
        _("Monto INATUR"),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Contribución parafiscal Turismo (1%)."),
    )

    # Relacion para ND/NC
    factura_asociada = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_relacionados",
        verbose_name=_("Factura Asociada (Para ND/NC)"),
    )

    class EstadoFactura(models.TextChoices):
        BORRADOR = "BOR", _("Borrador")
        EMITIDA = "EMI", _("Emitida (Pendiente de Pago)")
        PARCIAL = "PAR", _("Pagada Parcialmente")
        PAGADA = "PAG", _("Pagada Totalmente")
        VENCIDA = "VEN", _("Vencida")
        ANULADA = "ANU", _("Anulada")

    estado = models.CharField(
        _("Estado de la Factura"),
        max_length=3,
        choices=EstadoFactura.choices,
        default=EstadoFactura.BORRADOR,
    )
    notas = models.TextField(_("Notas de la Factura"), blank=True, null=True)
    asiento_contable_factura = models.ForeignKey(
        "contabilidad.AsientoContable",
        related_name="finance_facturas_asociadas",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Asiento Contable de Factura"),
    )
    archivo_pdf = models.FileField(
        _("Archivo PDF"), upload_to="facturas/%Y/%m/", blank=True, null=True
    )

    # === NUEVOS CAMPOS ADICIONALES PARA MERGE DE FACTURA CONSOLIDADA VENEZUELA ===
    emisor_rif = models.CharField(_("RIF Emisor"), max_length=20, blank=True)
    emisor_razon_social = models.CharField(_("Razón Social Emisor"), max_length=200, blank=True)
    emisor_direccion_fiscal = models.TextField(_("Dirección Fiscal Emisor"), blank=True)
    es_sujeto_pasivo_especial = models.BooleanField(
        _("Es Sujeto Pasivo Especial"),
        default=False,
        help_text=_("Determina obligaciones como agente de percepción IGTF"),
    )
    esta_inscrita_rtn = models.BooleanField(
        _("Inscrita en RTN"), default=False, help_text=_("Registro Turístico Nacional")
    )

    cliente_es_residente = models.BooleanField(
        _("Cliente es Residente"),
        default=True,
        help_text=_("Determina si aplica exportación de servicios (alícuota 0%)"),
    )
    cliente_identificacion = models.CharField(
        _("Identificación Cliente"),
        max_length=50,
        blank=True,
        help_text=_("Cédula, RIF o Pasaporte"),
    )
    cliente_direccion = models.TextField(_("Dirección Cliente"), blank=True)

    class TipoOperacion(models.TextChoices):
        VENTA_PROPIA = "VENTA_PROPIA", _("Venta Propia")
        INTERMEDIACION = "INTERMEDIACION", _("Intermediación")

    tipo_operacion = models.CharField(
        _("Tipo de Operación"),
        max_length=20,
        choices=TipoOperacion.choices,
        default=TipoOperacion.VENTA_PROPIA,
    )

    class MonedaOperacion(models.TextChoices):
        BOLIVAR = "BOLIVAR", _("Bolívar")
        DIVISA = "DIVISA", _("Divisa")

    moneda_operacion = models.CharField(
        _("Moneda de Operación"),
        max_length=10,
        choices=MonedaOperacion.choices,
        default=MonedaOperacion.DIVISA,
    )
    tasa_cambio_bcv = models.DecimalField(
        _("Tasa de Cambio BCV"),
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
        help_text=_("Tasa oficial BCV del día de la operación"),
    )

    subtotal_base_gravada = models.DecimalField(
        _("Base Gravada 16%"), max_digits=12, decimal_places=2, default=0
    )
    subtotal_exento = models.DecimalField(
        _("Base Exenta"), max_digits=12, decimal_places=2, default=0
    )
    subtotal_exportacion = models.DecimalField(
        _("Base Exportación 0%"), max_digits=12, decimal_places=2, default=0
    )

    monto_iva_16 = models.DecimalField(_("IVA 16%"), max_digits=12, decimal_places=2, default=0)
    monto_iva_adicional = models.DecimalField(
        _("IVA Adicional Divisas"), max_digits=12, decimal_places=2, default=0
    )
    monto_igtf = models.DecimalField(_("IGTF 3%"), max_digits=12, decimal_places=2, default=0)

    subtotal_base_gravada_bs = models.DecimalField(
        _("Base Gravada Bs"), max_digits=15, decimal_places=2, blank=True, null=True
    )
    subtotal_exento_bs = models.DecimalField(
        _("Base Exenta Bs"), max_digits=15, decimal_places=2, blank=True, null=True
    )
    monto_iva_16_bs = models.DecimalField(
        _("IVA 16% Bs"), max_digits=15, decimal_places=2, blank=True, null=True
    )
    monto_igtf_bs = models.DecimalField(
        _("IGTF Bs"), max_digits=15, decimal_places=2, blank=True, null=True
    )
    monto_total_bs = models.DecimalField(
        _("Total Bs"), max_digits=15, decimal_places=2, blank=True, null=True
    )

    tercero_rif = models.CharField(_("RIF Tercero"), max_length=20, blank=True)
    tercero_razon_social = models.CharField(_("Razón Social Tercero"), max_length=200, blank=True)

    class ModalidadEmision(models.TextChoices):
        DIGITAL = "DIGITAL", _("Digital")
        CONTINGENCIA_FISICA = "CONTINGENCIA_FISICA", _("Contingencia Física")

    modalidad_emision = models.CharField(
        _("Modalidad de Emisión"),
        max_length=20,
        choices=ModalidadEmision.choices,
        default=ModalidadEmision.DIGITAL,
    )
    firma_digital = models.TextField(_("Firma Digital"), blank=True, null=True)

    class Meta:
        verbose_name = _("Factura de Cliente")
        verbose_name_plural = _("Facturas de Clientes")
        ordering = ["-fecha_emision", "-numero_factura"]
        indexes = [
            models.Index(fields=["numero_factura"]),
            models.Index(fields=["numero_control"]),
            models.Index(fields=["fecha_emision"]),
            models.Index(fields=["tipo_factura"]),
            models.Index(fields=["agencia_id", "fecha_emision"]),
            models.Index(fields=["agencia_id", "estado"]),
            models.Index(fields=["venta_asociada_id"]),
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_factura_soft_delete_saas"),
        ]

    def __str__(self):
        return self.numero_factura or f"FACT-{self.id_factura}"

    def clean(self):
        super().clean()
        if self.monto_total < 0:
            raise ValidationError({"monto_total": _("El monto total no puede ser negativo.")})
        if self.subtotal < 0:
            raise ValidationError({"subtotal": _("El subtotal no puede ser negativo.")})
        if self.monto_impuestos < 0:
            raise ValidationError({"monto_impuestos": _("Los impuestos no pueden ser negativos.")})
        if self.saldo_pendiente < 0:
            raise ValidationError(
                {"saldo_pendiente": _("El saldo pendiente no puede ser negativo.")}
            )
        if self.estado == self.EstadoFactura.PAGADA and self.saldo_pendiente > 0:
            raise ValidationError(
                {"estado": _("No se puede marcar como pagada con saldo pendiente.")}
            )

        # Validaciones de Facturación Venezolana
        if getattr(self, "tipo_operacion", None) == self.TipoOperacion.INTERMEDIACION:
            if not getattr(self, "tercero_rif", None) or not getattr(
                self, "tercero_razon_social", None
            ):
                raise ValidationError(
                    {
                        "tercero_rif": _(
                            "El RIF del tercero es obligatorio para operaciones de intermediación."
                        ),
                        "tercero_razon_social": _(
                            "La razón social del tercero es obligatoria para operaciones de intermediación."
                        ),
                    }
                )

        if getattr(self, "moneda_operacion", None) == self.MonedaOperacion.DIVISA and not getattr(
            self, "tasa_cambio_bcv", None
        ):
            raise ValidationError(
                {
                    "tasa_cambio_bcv": _(
                        "La tasa de cambio oficial BCV es obligatoria para operaciones pactadas en divisas."
                    )
                }
            )

    def recalcular_totales(self):
        """Calcula bases, impuestos y totales basados en los items."""
        base_gravada = Decimal(0)
        base_exenta = Decimal(0)

        items = self.items_factura.all()
        if items.exists():
            for item in items:
                if item.tipo_impuesto in ["16", "25", "08"]:
                    base_gravada += item.subtotal_item
                else:
                    base_exenta += item.subtotal_item

        self.base_imponible = base_gravada
        self.base_exenta = base_exenta

        self.iva_monto = (self.base_imponible * (self.iva_porcentaje / Decimal(100))).quantize(
            Decimal("0.01")
        )
        self.subtotal = self.base_imponible + self.base_exenta

        # INATUR (1%) sobre el subtotal del servicio turístico
        self.inatur_monto = (self.subtotal * (self.inatur_porcentaje / Decimal(100))).quantize(
            Decimal("0.01")
        )

        # IGTF (3%) sobre el total a pagar en divisas
        self.igtf_monto = (
            (self.subtotal + self.iva_monto + self.inatur_monto)
            * (self.igtf_porcentaje / Decimal(100))
        ).quantize(Decimal("0.01"))

        self.monto_impuestos = self.iva_monto + self.igtf_monto + self.inatur_monto
        self.monto_total = self.subtotal + self.monto_impuestos

        if self.saldo_pendiente is None or self.estado == self.EstadoFactura.BORRADOR:
            self.saldo_pendiente = self.monto_total

    def calcular_impuestos_venezuela(self):
        """
        Calcula bases, impuestos y totales para la normativa venezolana,
        asegurando total retrocompatibilidad con la suite de tests.
        """
        base_gravada = Decimal(0)
        base_exenta = Decimal(0)
        base_exportacion = Decimal(0)
        monto_iva = Decimal(0)

        # Usar los items relacionados
        items = self.items_factura.all()
        for item in items:
            subtotal_item = (item.precio_unitario * item.cantidad).quantize(Decimal("0.01"))

            tipo_servicio = getattr(item, "tipo_servicio", None)
            es_gravado = getattr(item, "es_gravado", True)
            alicuota = getattr(item, "alicuota_iva", Decimal("25.00"))

            if tipo_servicio == "TRANSPORTE_AEREO_NACIONAL" or not es_gravado:
                base_exenta += subtotal_item
            elif tipo_servicio == "SERVICIO_EXPORTACION":
                base_exportacion += subtotal_item
            else:
                base_gravada += subtotal_item
                monto_iva += (subtotal_item * (alicuota / Decimal("100.00"))).quantize(
                    Decimal("0.01")
                )

        self.subtotal_base_gravada = base_gravada
        self.subtotal_exento = base_exenta
        self.subtotal_exportacion = base_exportacion
        self.monto_iva_16 = monto_iva

        # IGTF (3%) si es sujeto pasivo especial y se paga en divisas
        if self.es_sujeto_pasivo_especial and self.moneda_operacion == "DIVISA":
            base_igtf = (
                self.subtotal_base_gravada
                + self.monto_iva_16
                + self.subtotal_exento
                + self.subtotal_exportacion
            )
            self.monto_igtf = (base_igtf * Decimal("0.03")).quantize(Decimal("0.01"))
        else:
            self.monto_igtf = Decimal("0.00")

        self.subtotal = (
            self.subtotal_base_gravada + self.subtotal_exento + self.subtotal_exportacion
        ).quantize(Decimal("0.01"))
        self.monto_total = (self.subtotal + self.monto_iva_16 + self.monto_igtf).quantize(
            Decimal("0.01")
        )

        if self.venta_asociada:
            self.saldo_pendiente = max(
                Decimal("0.00"),
                self.monto_total - (self.venta_asociada.monto_pagado or Decimal("0.00")),
            )
        elif self.estado == self.EstadoFactura.BORRADOR:
            self.saldo_pendiente = self.monto_total

        self.save()

    @property
    def monto_pagado(self):
        """Monto pagado calculado a partir del total y el saldo pendiente."""
        if self.venta_asociada:
            return self.venta_asociada.monto_pagado
        return max(Decimal("0.00"), self.monto_total - self.saldo_pendiente)

    def get_display_name(self):
        """Devuelve el nombre del cliente o la descripción del primer item como fallback."""
        if self.cliente:
            return self.cliente.get_nombre_completo()

        # Fallback al primer item de la venta asociada
        if self.venta_asociada:
            primer_item = self.venta_asociada.items_venta.first()
            if primer_item:
                return primer_item.descripcion_personalizada

        return "Cliente no identificado"

    def save(self, *args, **kwargs):
        es_creacion = self.pk is None

        if not self.numero_factura:
            self.numero_factura = generar_numero_factura_atomico(self.__class__, self.fecha_emision)

        # Snapshot cliente
        if self.cliente and not self.cliente_rif:
            try:
                self.cliente_nombre = self.cliente.get_nombre_completo()
                self.cliente_rif = (
                    getattr(self.cliente, "numero_documento", "")
                    or getattr(self.cliente, "cedula_identidad", "")
                    or ""
                )
                self.cliente_direccion = getattr(self.cliente, "direccion_linea1", "") or ""
                self.cliente_telefono = self.cliente.telefono_principal or ""
            except Exception as e:
                logger.warning(f"Excepción silenciosa capturada al tomar snapshot: {e}")

        # Sincronizar las dos tasas (tasa_cambio y tasa_cambio_bcv)
        if self.tasa_cambio_bcv and (not self.tasa_cambio or self.tasa_cambio == 1):
            self.tasa_cambio = self.tasa_cambio_bcv
        elif self.tasa_cambio and (not self.tasa_cambio_bcv or self.tasa_cambio_bcv == 1):
            self.tasa_cambio_bcv = self.tasa_cambio

        # Si viene de la lógica Consolidada, calcular totales en USD
        if (
            self.subtotal_base_gravada
            or self.subtotal_exento
            or self.subtotal_exportacion
            or self.monto_iva_16
            or self.monto_igtf
        ):
            self.subtotal = (
                Decimal(str(self.subtotal_base_gravada or 0))
                + Decimal(str(self.subtotal_exento or 0))
                + Decimal(str(self.subtotal_exportacion or 0))
            ).quantize(Decimal("0.01"))
            self.monto_total = (
                self.subtotal
                + Decimal(str(self.monto_iva_16 or 0))
                + Decimal(str(self.monto_iva_adicional or 0))
                + Decimal(str(self.monto_igtf or 0))
            ).quantize(Decimal("0.01"))

        # Convertir a Bolívares si hay tasa
        if self.tasa_cambio_bcv:
            self.subtotal_base_gravada_bs = (
                Decimal(str(self.subtotal_base_gravada or 0)) * self.tasa_cambio_bcv
            ).quantize(Decimal("0.01"))
            self.subtotal_exento_bs = (
                Decimal(str(self.subtotal_exento or 0)) * self.tasa_cambio_bcv
            ).quantize(Decimal("0.01"))
            self.monto_iva_16_bs = (
                Decimal(str(self.monto_iva_16 or 0)) * self.tasa_cambio_bcv
            ).quantize(Decimal("0.01"))
            self.monto_igtf_bs = (
                Decimal(str(self.monto_igtf or 0)) * self.tasa_cambio_bcv
            ).quantize(Decimal("0.01"))
            self.monto_total_bs = (self.monto_total * self.tasa_cambio_bcv).quantize(
                Decimal("0.01")
            )

        if self.venta_asociada:
            self.saldo_pendiente = max(
                Decimal("0.00"),
                self.monto_total - (self.venta_asociada.monto_pagado or Decimal("0.00")),
            )
        elif es_creacion:
            self.saldo_pendiente = self.monto_total

        # Actualizar estado según saldo
        if self.estado in {
            self.EstadoFactura.BORRADOR,
            self.EstadoFactura.EMITIDA,
            self.EstadoFactura.PARCIAL,
            self.EstadoFactura.PAGADA,
        }:
            if self.saldo_pendiente <= 0 and self.monto_total > 0:
                self.estado = self.EstadoFactura.PAGADA
            elif 0 < self.saldo_pendiente < self.monto_total:
                self.estado = self.EstadoFactura.PARCIAL
            elif self.estado == self.EstadoFactura.BORRADOR and self.monto_total > 0:
                self.estado = self.EstadoFactura.EMITIDA

        self.full_clean()
        super().save(*args, **kwargs)


class ItemFactura(AgenciaMixin, SoftDeleteModel, models.Model):
    id_item_factura = models.AutoField(primary_key=True, verbose_name=_("ID Item Factura"))
    factura = models.ForeignKey(
        Factura, related_name="items_factura", on_delete=models.PROTECT, verbose_name=_("Factura")
    )
    descripcion = models.CharField(_("Descripción del Item"), max_length=500)
    cantidad = models.DecimalField(_("Cantidad"), max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(_("Precio Unitario"), max_digits=12, decimal_places=2)
    subtotal_item = models.DecimalField(
        _("Subtotal Item"), max_digits=12, decimal_places=2, editable=False
    )

    class TipoImpuesto(models.TextChoices):
        IVA_25 = "25", _("IVA General (25%)")
        IVA_16 = "16", _("IVA General Legacy (16%)")
        IVA_8 = "08", _("IVA Reducido (8%)")
        EXENTO = "00", _("Exento / No Sujeto")

    tipo_impuesto = models.CharField(
        _("Tipo Impuesto"), max_length=2, choices=TipoImpuesto.choices, default=TipoImpuesto.IVA_25
    )

    # === NUEVOS CAMPOS ADICIONALES PARA MERGE DE ITEMFACTURA CONSOLIDADA VENEZUELA ===
    class TipoServicio(models.TextChoices):
        COMISION_INTERMEDIACION = "COMISION_INTERMEDIACION", _("Comisión Intermediación")
        TRANSPORTE_AEREO_NACIONAL = "TRANSPORTE_AEREO_NACIONAL", _("Transporte Aéreo Nacional")
        ALOJAMIENTO_Y_OTROS_GRAVADOS = (
            "ALOJAMIENTO_Y_OTROS_GRAVADOS",
            _("Alojamiento y Otros Gravados"),
        )
        SERVICIO_EXPORTACION = "SERVICIO_EXPORTACION", _("Servicio Exportación")

    tipo_servicio = models.CharField(
        _("Tipo de Servicio"),
        max_length=30,
        choices=TipoServicio.choices,
        default=TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
    )
    es_gravado = models.BooleanField(_("Es Gravado"), default=True)
    alicuota_iva = models.DecimalField(
        _("Alícuota IVA"), max_digits=5, decimal_places=2, default=Decimal("25.00")
    )

    nombre_pasajero = models.CharField(_("Nombre Pasajero"), max_length=200, blank=True)
    numero_boleto = models.CharField(_("Número Boleto"), max_length=50, blank=True)
    itinerario = models.TextField(_("Itinerario"), blank=True)
    codigo_aerolinea = models.CharField(_("Código Aerolínea"), max_length=10, blank=True)

    class Meta:
        verbose_name = _("Item de Factura")
        verbose_name_plural = _("Items de Factura")
        indexes = [
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_itemfact_soft_delete_saas"),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.descripcion} en Factura {self.factura.numero_factura}"

    def clean(self):
        super().clean()
        if getattr(self, "tipo_servicio", None) == self.TipoServicio.TRANSPORTE_AEREO_NACIONAL:
            errors = {}
            if not getattr(self, "nombre_pasajero", None):
                errors["nombre_pasajero"] = _(
                    "El nombre del pasajero es obligatorio para boletos aéreos."
                )
            if not getattr(self, "numero_boleto", None):
                errors["numero_boleto"] = _(
                    "El número de boleto es obligatorio para boletos aéreos."
                )
            if not getattr(self, "itinerario", None):
                errors["itinerario"] = _("El itinerario es obligatorio para boletos aéreos.")
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.subtotal_item = (self.precio_unitario * self.cantidad).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

        try:
            if hasattr(self.factura, "calcular_impuestos_venezuela"):
                self.factura.calcular_impuestos_venezuela()
            else:
                self.factura.recalcular_totales()
                self.factura.save()
        except Exception:
            logger.exception(f"Failed to recalculate totals for Factura {self.factura_id}")


class DocumentoExportacion(models.Model):
    """Documentos de soporte para exportación de servicios (turismo receptivo)"""

    class TipoDocumento(models.TextChoices):
        PASAPORTE = "PASAPORTE", _("Pasaporte")
        COMPROBANTE_PAGO = "COMPROBANTE_PAGO", _("Comprobante Pago Internacional")
        OTRO = "OTRO", _("Otro")

    factura = models.ForeignKey(
        Factura,
        related_name="documentos_exportacion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    tipo_documento = models.CharField(
        _("Tipo Documento"), max_length=20, choices=TipoDocumento.choices
    )
    numero_documento = models.CharField(_("Número Documento"), max_length=100)
    archivo = models.FileField(
        _("Archivo"), upload_to="documentos_exportacion/%Y/%m/", blank=True, null=True
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Documento Exportación")
        verbose_name_plural = _("Documentos Exportación")

    def __str__(self):
        return f"{self.get_tipo_documento_display()} - {self.numero_documento}"


class ReporteProveedor(AgenciaMixin, models.Model):
    """
    DEPRECADO: Usar apps.finance.models.reconciliacion.ReporteReconciliacion en su lugar.
    Este modelo será eliminado en v3.0.
    """

    class EstadoReporte(models.TextChoices):
        PENDIENTE = "PEN", _("Pendiente por Procesar")
        PROCESADO = "PRO", _("Procesado")
        ERROR = "ERR", _("Error en Procesamiento")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn(
            "ReporteProveedor is deprecated. Use reconciliacion.ReporteReconciliacion instead. "
            "This model will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )

    proveedor = models.ForeignKey(
        "bookings.Proveedor", on_delete=models.CASCADE, related_name="reportes_finance"
    )
    agencia = models.ForeignKey(
        "core.Agencia", on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Agencia")
    )
    archivo = models.FileField(_("Archivo de Reporte"), upload_to="finanzas/reportes/%Y/%m/")
    fecha_carga = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        _("Estado"), max_length=3, choices=EstadoReporte.choices, default=EstadoReporte.PENDIENTE
    )

    total_registros = models.IntegerField(default=0)
    total_con_diferencia = models.IntegerField(default=0)

    notas = models.TextField(blank=True)

    def __str__(self):
        return f"Reporte {self.proveedor.nombre} - {self.fecha_carga.strftime('%d/%m/%Y')}"

    class Meta:
        verbose_name = _("Reporte de Proveedor")
        verbose_name_plural = _("Reportes de Proveedores")


class ItemReporte(AgenciaMixin, models.Model):
    """
    DEPRECADO: Usar reconciliacion.LineaReporteReconciliacion en su lugar.
    Este modelo será eliminado en v3.0.
    """

    class EstadoConciliacion(models.TextChoices):
        MATCH = "MAT", _("Conciliado (OK)")
        DISCREPANCY = "DIS", _("Discrepancia detectada")
        MISSING_INTERNAL = "MIN", _("Falta en sistema (Solo en reporte)")
        MISSING_PROVIDER = "MPR", _("Falta en reporte (Solo en sistema)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn(
            "ItemReporte is deprecated. Use reconciliacion.LineaReporteReconciliacion instead. "
            "This model will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )

    reporte = models.ForeignKey(ReporteProveedor, on_delete=models.CASCADE, related_name="items")
    numero_boleto = models.CharField(_("Número de Boleto"), max_length=50)

    pnr = models.CharField(_("PNR"), max_length=10, blank=True, null=True)
    pasajero = models.CharField(_("Pasajero"), max_length=200, blank=True, null=True)
    fecha_emision = models.DateField(_("Fecha Emisión"), null=True, blank=True)

    monto_total_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    monto_sistema = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_proveedor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comision_proveedor = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Vinculación con registro interno
    boleto_interno = models.ForeignKey(
        "bookings.BoletoImportado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_reconciliacion",
    )

    estado = models.CharField(
        max_length=3, choices=EstadoConciliacion.choices, default=EstadoConciliacion.MATCH
    )
    fecha_conciliacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.numero_boleto} - {self.estado}"


class DiferenciaFinanciera(AgenciaMixin, models.Model):
    """
    DEPRECADO: Usar reconciliacion.ConciliacionBoleto (campo diferencia_*) en su lugar.
    Este modelo será eliminado en v3.0.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn(
            "DiferenciaFinanciera is deprecated. Use reconciliacion.ConciliacionBoleto instead. "
            "This model will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )

    item_reporte = models.ForeignKey(
        ItemReporte, on_delete=models.CASCADE, related_name="diferencias"
    )
    campo_discrepancia = models.CharField(max_length=50)  # 'monto_total', 'tax', 'comision'
    valor_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    valor_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)

    resuelto = models.BooleanField(default=False)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "OK" if self.resuelto else "PEND"
        return f"Dif #{self.pk} {self.campo_discrepancia}: {self.diferencia} [{status}]"


class GastoOperativo(AgenciaMixin, SoftDeleteModel, models.Model):
    id_gasto = models.AutoField(primary_key=True, verbose_name=_("ID Gasto"))
    # agencia la provee AgenciaMixin
    descripcion = models.CharField(_("Descripción"), max_length=255)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    fecha = models.DateField(_("Fecha"), default=timezone.now)
    categoria = models.CharField(_("Categoría"), max_length=100, blank=True, null=True)
    comprobante = models.FileField(
        _("Comprobante/Factura"), upload_to="gastos/%Y/%m/", blank=True, null=True
    )
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    creado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Registrado por"),
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # --- CONTROL CONTABLE (Audit Point 3) ---
    asiento_contable = models.ForeignKey(
        "contabilidad.AsientoContable",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Asiento Contable Asociado"),
    )

    class EstadoContable(models.TextChoices):
        PENDIENTE = "PEN", _("Pendiente de Contabilizar")
        PROCESADO = "PRO", _("Contabilizado Correctamente")
        ERROR = "ERR", _("Error de Configuración Contable")

    estado_contable = models.CharField(
        _("Estado Contable"),
        max_length=3,
        choices=EstadoContable.choices,
        default=EstadoContable.PENDIENTE,
    )
    error_contable_msg = models.TextField(
        _("Mensaje de Error Contable"),
        blank=True,
        null=True,
        help_text=_("Indica por qué no se pudo generar el asiento automático."),
    )

    class Meta:
        verbose_name = _("Gasto Operativo")
        verbose_name_plural = _("Gastos Operativos")
        ordering = ["-fecha", "-fecha_registro"]
        indexes = [
            models.Index(fields=["is_deleted", "agencia"], name="idx_gasto_soft_delete_saas"),
        ]

    def __str__(self):
        return f"{self.fecha} - {self.descripcion} ({self.monto} {self.moneda})"


class PagoBinance(AgenciaMixin, SoftDeleteModel, models.Model):
    class EstadoPago(models.TextChoices):
        INICIAL = "INI", _("Inicial / Pendiente")
        PROCESANDO = "PRO", _("Procesando")
        EXITOSO = "EXI", _("Exitoso")
        FALLIDO = "FAL", _("Fallido")
        EXPIRADO = "EXP", _("Expirado")

    id_pago_binance = models.AutoField(primary_key=True)
    factura = models.ForeignKey(
        Factura, on_delete=models.PROTECT, related_name="pagos_binance", verbose_name=_("Factura")
    )

    # Binance Specifics
    prepay_id = models.CharField(_("Binance Prepay ID"), max_length=100, blank=True, null=True)
    merchant_trade_no = models.CharField(_("Internal Trade Number"), max_length=50, unique=True)
    checkout_url = models.URLField(_("Checkout URL"), max_length=500, blank=True, null=True)

    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.CharField(_("Moneda"), max_length=5, default="USDT")

    estado = models.CharField(
        _("Estado"), max_length=3, choices=EstadoPago.choices, default=EstadoPago.INICIAL
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    raw_response = models.JSONField(_("Respuesta API Binance"), default=dict, blank=True)

    class Meta:
        verbose_name = _("Pago Binance Pay")
        verbose_name_plural = _("Pagos Binance Pay")
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Pago {self.merchant_trade_no} - {self.factura.numero_factura} ({self.get_estado_display()})"


class TransaccionPago(AgenciaMixin, SoftDeleteModel, models.Model):
    """
    Modelo blindado para registrar pagos provenientes de Webhooks externos.
    La clave es 'webhook_transaction_id' con unique=True para garantizar idempotencia.
    """

    class ProveedorPago(models.TextChoices):
        BINANCE = "BIN", _("Binance Pay")
        STRIPE = "STR", _("Stripe")
        ZELLE = "ZEL", _("Zelle")
        OTRO = "OTR", _("Otro")

    id_transaccion = models.AutoField(primary_key=True)
    proveedor = models.CharField(_("Proveedor"), max_length=3, choices=ProveedorPago.choices)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.CharField(_("Moneda"), max_length=10, default="USD")

    # Vinculación con la venta (Uso de string para evitar circularidad)
    venta = models.ForeignKey(
        "bookings.Venta",
        on_delete=models.PROTECT,
        related_name="transacciones_pago",
        verbose_name=_("Venta"),
    )

    # El campo más importante para el blindaje
    webhook_transaction_id = models.CharField(
        _("Webhook Transaction ID"),
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("ID único de la pasarela (ej. TransactionID de Binance o pi_XXX de Stripe)."),
    )

    data_raw = models.JSONField(_("Datos Raw del Webhook"), default=dict, blank=True)
    fecha_registro = models.DateTimeField(_("Fecha Registro"), auto_now_add=True)

    class Meta:
        verbose_name = _("Transacción de Pago")
        verbose_name_plural = _("Transacciones de Pago")
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.get_proveedor_display()} - {self.webhook_transaction_id}"


class PropuestaTransaccionIA(AgenciaMixin, SoftDeleteModel, models.Model):
    """
    Staging Ledger Buffer para transacciones contables y financieras sugeridas
    por la Inteligencia Artificial que requieren validación de un CFO.
    """

    class EstadoPropuesta(models.TextChoices):
        PENDIENTE = "PEN", _("Pendiente de Aprobación")
        APROBADA = "APR", _("Aprobada y Procesada")
        RECHAZADA = "REC", _("Rechazada")

    id_propuesta = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Metadatos del Negocio
    modulo_objetivo = models.CharField(
        _("Módulo Objetivo"), max_length=50
    )  # 'CONTABILIDAD', 'FINANZAS', 'RECONCILIACION'
    accion_tipo = models.CharField(
        _("Tipo de Acción"), max_length=50
    )  # 'CREAR_ASIENTO', 'CONCILIAR_BOLETO', 'REGISTRAR_GASTO'

    # Carga útil estructurada de la transacción
    payload_datos = models.JSONField(
        _("Payload de Datos"),
        help_text=_("Datos exactos a procesar determinísticamente al aprobar"),
    )
    ia_justificacion = models.TextField(
        _("Justificación de la IA"),
        help_text=_("Explicación y razonamiento en lenguaje natural de la IA"),
    )

    # Estados de Aprobación
    estado = models.CharField(
        _("Estado"),
        max_length=3,
        choices=EstadoPropuesta.choices,
        default=EstadoPropuesta.PENDIENTE,
    )
    fecha_creacion = models.DateTimeField(_("Fecha Creación"), auto_now_add=True)
    fecha_resolucion = models.DateTimeField(_("Fecha Resolución"), null=True, blank=True)
    usuario_resolutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="propuestas_ia_resueltas",
        verbose_name=_("Usuario Resolutor"),
    )
    comentarios_resolucion = models.TextField(_("Comentarios de Resolución"), blank=True, null=True)

    class Meta:
        verbose_name = _("Propuesta Transacción IA")
        verbose_name_plural = _("Propuestas Transacción IA")
        db_table = "finance_propuesta_transaccion_ia"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Propuesta IA - {self.accion_tipo} ({self.get_estado_display()})"

    @property
    def justificacion(self):
        return self.ia_justificacion

    @justificacion.setter
    def justificacion(self, value):
        self.ia_justificacion = value

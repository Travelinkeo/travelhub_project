from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models_catalogos import Moneda

from ..validators import validar_no_vacio_o_espacios


class AsientoContable(models.Model):
    id_asiento = models.AutoField(primary_key=True, verbose_name=_("ID Asiento"))
    numero_asiento = models.CharField(_("Número de Asiento"), max_length=20, unique=True, blank=True)
    fecha_contable = models.DateField(_("Fecha Contable"), default=timezone.now)
    descripcion_general = models.CharField(_("Descripción General"), max_length=255)
    class TipoAsiento(models.TextChoices):
        DIARIO = 'DIA', _('Diario')
        COMPRAS = 'COM', _('Compras')
        VENTAS = 'VEN', _('Ventas')
        NOMINA = 'NOM', _('Nómina')
        APERTURA = 'APE', _('Apertura')
        CIERRE = 'CIE', _('Cierre')
        AJUSTE = 'AJU', _('Ajuste')
    tipo_asiento = models.CharField(_("Tipo de Asiento"), max_length=3, choices=TipoAsiento.choices, default=TipoAsiento.DIARIO)
    referencia_documento = models.CharField(_("Referencia Documento"), max_length=100, blank=True, null=True, help_text=_('Ej: Factura #, Reserva #'))
    class EstadoAsiento(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        CONTABILIZADO = 'CON', _('Contabilizado')
        ANULADO = 'ANU', _('Anulado')
    EstadoAsientoChoices = EstadoAsiento
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoAsiento.choices, default=EstadoAsiento.BORRADOR)
    tasa_cambio_aplicada = models.DecimalField(_("Tasa de Cambio Aplicada"), max_digits=18, decimal_places=8, default=1.0, help_text=_('Respecto a la moneda local, si aplica.'))
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_('Moneda del Asiento'), related_name='core_asientos_contables')
    fecha_creacion = models.DateTimeField(_("Fecha de Creación"), auto_now_add=True)
    total_debe = models.DecimalField(_("Total Debe"), max_digits=15, decimal_places=2, default=0, editable=False)
    total_haber = models.DecimalField(_("Total Haber"), max_digits=15, decimal_places=2, default=0, editable=False)

    class Meta:
        verbose_name = _("Asiento Contable")
        verbose_name_plural = _("Asientos Contables")
        ordering = ['-fecha_contable', '-numero_asiento']

    def __str__(self):
        return f"Asiento {self.numero_asiento or self.id_asiento}"

    def calcular_totales(self, commit=True):
        from django.db.models import Sum
        agregados = self.detalles_asiento.aggregate(s_debe=Sum('debe'), s_haber=Sum('haber'))
        self.total_debe = agregados.get('s_debe') or 0
        self.total_haber = agregados.get('s_haber') or 0
        if commit:
            super().save(update_fields=['total_debe', 'total_haber'])
        return self.total_debe, self.total_haber

    @property
    def esta_cuadrado(self):
        try:
            return (self.total_debe or 0) == (self.total_haber or 0)
        except Exception:
            return False

class PlanContable(models.Model):
    id_cuenta = models.AutoField(primary_key=True, verbose_name=_("ID Cuenta"))
    codigo_cuenta = models.CharField(_("Código de Cuenta"), max_length=30, unique=True, validators=[validar_no_vacio_o_espacios])
    nombre_cuenta = models.CharField(_("Nombre de la Cuenta"), max_length=100, validators=[validar_no_vacio_o_espacios])
    class TipoCuentaChoices(models.TextChoices):
        ACTIVO = 'AC', _('Activo')
        PASIVO = 'PA', _('Pasivo')
        PATRIMONIO = 'PT', _('Patrimonio')
        INGRESO = 'IN', _('Ingreso')
        GASTO = 'GA', _('Gasto/Costo')
        CUENTA_ORDEN = 'CO', _('Cuenta de Orden')
    tipo_cuenta = models.CharField(_("Tipo de Cuenta"), max_length=2, choices=TipoCuentaChoices.choices)
    nivel = models.PositiveSmallIntegerField(_("Nivel Jerárquico"), default=1)
    cuenta_padre = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='subcuentas', verbose_name=_("Cuenta Padre"))
    permite_movimientos = models.BooleanField(_("Permite Movimientos"), default=True, help_text=_('Si es False, es una cuenta de agrupación.'))
    class NaturalezaChoices(models.TextChoices):
        DEUDORA = 'D', _('Deudora')
        ACREEDORA = 'H', _('Acreedora')
    naturaleza = models.CharField(_("Naturaleza"), max_length=1, choices=NaturalezaChoices.choices)
    descripcion = models.TextField(_("Descripción"), blank=True, null=True)

    class Meta:
        verbose_name = _("Cuenta Contable")
        verbose_name_plural = _("Plan de Cuentas")
        ordering = ['codigo_cuenta']

    def __str__(self):
        return f"{self.codigo_cuenta} - {self.nombre_cuenta}"

class DetalleAsiento(models.Model):
    id_detalle_asiento = models.AutoField(primary_key=True, verbose_name=_("ID Detalle Asiento"))
    asiento = models.ForeignKey(AsientoContable, related_name='detalles_asiento', on_delete=models.CASCADE, verbose_name=_('Asiento Contable'))
    linea = models.PositiveSmallIntegerField(_("Línea"), help_text=_('Número de línea dentro del asiento.'))
    cuenta_contable = models.ForeignKey(PlanContable, on_delete=models.PROTECT, verbose_name=_('Cuenta Contable'), limit_choices_to={'permite_movimientos': True})
    debe = models.DecimalField(_("Debe"), max_digits=15, decimal_places=2, default=0)
    haber = models.DecimalField(_("Haber"), max_digits=15, decimal_places=2, default=0)
    descripcion_linea = models.CharField(_("Descripción de la Línea"), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("Detalle de Asiento")
        verbose_name_plural = _("Detalles de Asientos")
        ordering = ['asiento', 'linea']
        unique_together = ('asiento', 'linea')

    def __str__(self):
        return f"Detalle {self.linea} de Asiento {self.asiento_id}"


class LiquidacionProveedor(models.Model):
    id_liquidacion = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey('core.Proveedor', on_delete=models.PROTECT, verbose_name=_("Proveedor"))
    venta = models.ForeignKey('core.Venta', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Venta Asociada"))
    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    monto_total = models.DecimalField(_("Monto Total a Pagar"), max_digits=12, decimal_places=2, default=0)
    monto_pagado = models.DecimalField(_("Monto Pagado"), max_digits=12, decimal_places=2, default=0)
    saldo_pendiente = models.DecimalField(_("Saldo Pendiente"), max_digits=12, decimal_places=2, default=0, editable=False)

    class EstadoLiquidacion(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente')
        PAGADA_PARCIAL = 'PAR', _('Pagada Parcialmente')
        PAGADA = 'PAG', _('Pagada')
        ANULADA = 'ANU', _('Anulada')

    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoLiquidacion.choices, default=EstadoLiquidacion.PENDIENTE)
    notas = models.TextField(_("Notas Internas"), blank=True, null=True)
    archivo_pdf = models.FileField(_("PDF de Liquidación"), upload_to='liquidaciones_proveedor/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = _("Liquidación a Proveedor")
        verbose_name_plural = _("Liquidaciones a Proveedores")
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Liquidación {self.id_liquidacion} a {self.proveedor}"

    def save(self, *args, **kwargs):
        self.saldo_pendiente = self.monto_total - self.monto_pagado
        super().save(*args, **kwargs)

class ItemLiquidacion(models.Model):
    id_item_liquidacion = models.AutoField(primary_key=True)
    liquidacion = models.ForeignKey(LiquidacionProveedor, related_name='items', on_delete=models.CASCADE, verbose_name=_("Liquidación"))
    item_venta = models.OneToOneField('core.ItemVenta', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Item de Venta Original"))
    descripcion = models.CharField(_("Descripción"), max_length=500)
    monto = models.DecimalField(_("Monto a Pagar"), max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _("Item de Liquidación")
        verbose_name_plural = _("Items de Liquidación")

    def __str__(self):
        return f"Item {self.descripcion} por {self.monto}"
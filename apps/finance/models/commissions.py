from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal

class ReglaComision(models.Model):
    """
    Define el motor de incentivos para los agentes de la agencia.
    Permite configurar pagos por volumen (fijo) o por rentabilidad (porcentaje).
    """
    class TipoCalculo(models.TextChoices):
        PORCENTAJE_UTILIDAD = 'UTIL', _('Porcentaje sobre Utilidad/Fee')
        PORCENTAJE_VENTA = 'VENTA', _('Porcentaje sobre Total Venta')
        MONTO_FIJO = 'FIJO', _('Monto Fijo por Boleto/Venta')

    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, verbose_name=_("Agencia"))
    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reglas_comision', verbose_name=_("Agente"))
    
    tipo_calculo = models.CharField(_("Tipo de Cálculo"), max_length=5, choices=TipoCalculo.choices, default=TipoCalculo.PORCENTAJE_UTILIDAD)
    valor = models.DecimalField(_("Valor (Propina/%)"), max_digits=12, decimal_places=2, help_text=_("Monto en $ o % según el tipo."))
    
    activo = models.BooleanField(_("Activo"), default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Regla de Comisión")
        verbose_name_plural = _("Reglas de Comisiones")
        unique_together = ('agencia', 'agente')

    def __str__(self):
        return f"Regla {self.agente.username} - {self.get_tipo_calculo_display()}"


class ComisionVenta(models.Model):
    """
    Registro individual de deuda con el agente por cada venta realizada.
    """
    class EstadoComision(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente de Liquidar')
        LIQUIDADO = 'LIQ', _('Liquidado en Nómina')
        CANCELADO = 'CAN', _('Cancelado (Venta Anulada)')

    venta = models.ForeignKey('bookings.Venta', on_delete=models.CASCADE, related_name='comisiones_agente', verbose_name=_("Venta"))
    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("Agente"))
    regla_aplicada = models.ForeignKey(ReglaComision, on_delete=models.SET_NULL, null=True, blank=True)
    
    monto_base_calculo = models.DecimalField(_("Monto Base"), max_digits=12, decimal_places=2, help_text=_("Total Venta o Utilidad usada para el cálculo."))
    monto_comision = models.DecimalField(_("Monto Comisión"), max_digits=12, decimal_places=2)
    
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoComision.choices, default=EstadoComision.PENDIENTE)
    
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    fecha_liquidacion = models.DateTimeField(_("Fecha de Liquidación"), null=True, blank=True)
    
    liquidacion_asociada = models.ForeignKey('LiquidacionAgente', on_delete=models.SET_NULL, null=True, blank=True, related_name='detalles_comisiones')

    class Meta:
        verbose_name = _("Comisión por Venta")
        verbose_name_plural = _("Comisiones por Ventas")
        ordering = ['-fecha_calculo']

    def __str__(self):
        return f"Comisión {self.monto_comision} - {self.agente.username}"


class LiquidacionAgente(models.Model):
    """
    Estado de cuenta mensual consolidado para el pago al agente.
    Actúa como el 'Recibo de Pago' oficial de la agencia.
    """
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE)
    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liquidaciones_mensuales')
    
    periodo_mes = models.IntegerField(_("Mes"), help_text="1-12")
    periodo_anio = models.IntegerField(_("Año"), help_text="YYYY")
    
    total_comisiones = models.DecimalField(_("Total Comisiones"), max_digits=12, decimal_places=2, default=0)
    cantidad_ventas = models.IntegerField(_("Cant. Ventas"), default=0)
    
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(_("Pagado/Transferido"), default=False)
    referencia_pago = models.CharField(_("Referencia de Pago"), max_length=100, blank=True)

    class Meta:
        verbose_name = _("Liquidación de Agente")
        verbose_name_plural = _("Liquidaciones de Agentes")
        unique_together = ('agente', 'periodo_mes', 'periodo_anio')

    def __str__(self):
        return f"Liquidación {self.periodo_mes}/{self.periodo_anio} - {self.agente.username}"

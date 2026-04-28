from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class ReporteReconciliacion(models.Model):
    """
    Modelo para almacenar reportes financieros (BSP, Kiu, etc.) subidos por la agencia
    para su conciliación automática.
    """
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Procesamiento'),
        ('PROCESANDO', 'Procesando con IA'),
        ('PROCESADO', 'Procesado Exitosamente'),
        ('ERROR', 'Error en Procesamiento'),
        ('CON_DISCREPANCIAS', 'Con Discrepancias Detectadas'),
        ('CONCILIADO', 'Conciliado Totalmente'),
    ]

    id_reporte = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, related_name='reportes_reconciliacion')
    archivo = models.FileField(upload_to='finance/reportes/%Y/%m/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    # Metadata del reporte
    proveedor = models.CharField(max_length=50, help_text="Ej: BSP, KIU, SABRE, AMADEUS")
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Resultados del parsing (JSON para flexibilidad)
    datos_extraidos = models.JSONField(null=True, blank=True, help_text="Raw data extraída por la IA")
    resumen_conciliacion = models.JSONField(null=True, blank=True, help_text="Resumen de match/mismatch")
    
    error_log = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Reporte de Reconciliación'
        verbose_name_plural = 'Reportes de Reconciliación'

    def __str__(self):
        return f"Reporte {self.proveedor} - {self.fecha_subida.strftime('%d/%m/%Y')} ({self.agencia.nombre})"


class LineaReporteReconciliacion(models.Model):
    """
    Cada fila individual extraída del PDF/CSV del Proveedor/BSP.
    Difiere del BoletoImportado, ya que esto dictamina lo que "Cobró" exactamente el proveedor en duro.
    """
    id_linea = models.AutoField(primary_key=True)
    reporte = models.ForeignKey(ReporteReconciliacion, on_delete=models.CASCADE, related_name='lineas')
    numero_boleto_reportado = models.CharField(_("Número de Boleto (Proveedor)"), max_length=150, db_index=True)
    
    tarifa_base_cobrada = models.DecimalField(_("Tarifa Base Cobrada"), max_digits=12, decimal_places=2, default=0)
    impuestos_cobrados = models.DecimalField(_("Impuestos Cobrados"), max_digits=12, decimal_places=2, default=0)
    comision_cedida = models.DecimalField(_("Comisión Cedida (-/+)"), max_digits=12, decimal_places=2, default=0)
    total_cobrado = models.DecimalField(_("Total Cobrado/Liquidado"), max_digits=12, decimal_places=2, default=0)
    
    raw_data = models.JSONField(_("Fila Cruda Original"), blank=True, null=True)

    class Meta:
        verbose_name = 'Linea de Reporte'
        verbose_name_plural = 'Líneas de Reporte'

    def __str__(self):
        return f"{self.numero_boleto_reportado} - {self.total_cobrado}"


class ConciliacionBoleto(models.Model):
    """
    Entidad de resolución. Entrelaza el "Boleto Original en Sistema" vs "El Cobro del Proveedor".
    """
    class EstadosCruce(models.TextChoices):
        OK = 'OK', _('Cuadrado Exacto')
        DISCREPANCIA = 'DISCREPANCIA', _('Diferencia Matemática')
        NO_EN_LOCAL = 'HUERFANO_PROVEEDOR', _('Cobrado, No existe en TravelHub')
        NO_EN_REPORTE = 'HUERFANO_LOCAL', _('En TravelHub, No fue cobrado por el Proveedor')
        IGNORADO = 'IGNORADO', _('Ignorado Manualmente')

    id_conciliacion = models.AutoField(primary_key=True)
    reporte = models.ForeignKey(ReporteReconciliacion, on_delete=models.CASCADE, related_name='conciliaciones')
    
    # Ambos pueden ser nulos si es huérfano de algún lado
    linea_reporte = models.OneToOneField(LineaReporteReconciliacion, on_delete=models.SET_NULL, null=True, blank=True)
    boleto_local = models.OneToOneField('bookings.BoletoImportado', on_delete=models.SET_NULL, null=True, blank=True)
    
    estado = models.CharField(max_length=20, choices=EstadosCruce.choices, default=EstadosCruce.OK)
    
    # Desviaciones (Reporte - Local) -> Positivo = Sobrecobro del Proveedor, Negativo = Proveedor cobró menos
    diferencia_tarifa = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    diferencia_impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    diferencia_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    sugerencia_asiento = models.ForeignKey('contabilidad.AsientoContable', on_delete=models.SET_NULL, null=True, blank=True, help_text="Asiento automático sugerido por IA")
    ia_razonamiento = models.TextField(blank=True, null=True, help_text="Explicación de la IA sobre el match difuso o discrepancia")
    resolucion_notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Conciliación de Boleto'
        verbose_name_plural = 'Conciliaciones de Boletos'

    def __str__(self):
        return f"Cruce: {self.estado} (Dif: {self.diferencia_total})"

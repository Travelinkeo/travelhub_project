from django.db import models
from django.db import models
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

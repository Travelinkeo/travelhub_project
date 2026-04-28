"""
Modelo para almacenar validaciones de requisitos migratorios.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class MigrationCheck(models.Model):
    """
    Registro de validaciones migratorias realizadas para pasajeros.
    
    Este modelo almacena el resultado de verificaciones automáticas de:
    - Requisitos de visa
    - Validez de pasaporte
    - Vacunas requeridas
    - Restricciones de tránsito
    """
    
    ALERT_LEVELS = [
        ('GREEN', '🟢 Todo en Orden'),
        ('YELLOW', '🟡 Requiere Atención'),
        ('RED', '🔴 Alerta Crítica'),
    ]
    
    # Relaciones
    pasajero = models.ForeignKey(
        'crm.Pasajero', 
        on_delete=models.CASCADE,
        related_name='migration_checks',
        verbose_name=_("Pasajero"),
        null=True,
        blank=True,
        help_text="Pasajero validado"
    )
    venta = models.ForeignKey(
        'bookings.Venta', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='migration_checks',
        help_text="Venta asociada (opcional)"
    )
    
    # Datos del viaje
    origen = models.CharField(
        max_length=3,
        null=True,
        blank=True,
        help_text="Código IATA del aeropuerto de origen (ej: CCS)"
    )
    destino = models.CharField(
        max_length=3,
        null=True,
        blank=True,
        help_text="Código IATA del aeropuerto de destino (ej: MAD)"
    )
    transitos = models.JSONField(
        default=list,
        help_text="Lista de códigos IATA de aeropuertos de tránsito (ej: ['PTY', 'MEX'])"
    )
    fecha_viaje = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha del primer vuelo"
    )
    
    # Resultados de la validación
    alert_level = models.CharField(
        max_length=10, 
        choices=ALERT_LEVELS,
        null=True,
        blank=True,
        help_text="Nivel de alerta resultante"
    )
    visa_required = models.BooleanField(
        null=True,
        blank=True,
        help_text="¿Requiere visa para el destino?"
    )
    visa_type = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Tipo de visa requerida (ej: 'Tourist', 'Transit', 'None')"
    )
    passport_validity_ok = models.BooleanField(
        null=True,
        blank=True,
        help_text="¿El pasaporte tiene validez suficiente?"
    )
    passport_min_months_required = models.IntegerField(
        default=6,
        help_text="Meses mínimos de validez requeridos"
    )
    vaccination_required = models.JSONField(
        default=list,
        help_text="Lista de vacunas requeridas (ej: ['Yellow Fever', 'COVID-19'])"
    )
    
    # Detalles y metadata
    summary = models.TextField(
        null=True,
        blank=True,
        help_text="Resumen legible de la validación"
    )
    full_report = models.JSONField(
        default=dict,
        help_text="Reporte completo en formato JSON"
    )
    
    # Auditoría
    checked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de la validación"
    )
    checked_by_ai = models.BooleanField(
        default=False,
        help_text="¿Se usó IA (Gemini) para esta validación?"
    )
    checked_by_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Usuario que solicitó la validación"
    )
    
    class Meta:
        ordering = ['-checked_at']
        verbose_name = "Validación Migratoria"
        verbose_name_plural = "Validaciones Migratorias"
        indexes = [
            models.Index(fields=['pasajero', '-checked_at']),
            models.Index(fields=['venta', '-checked_at']),
            models.Index(fields=['alert_level']),
        ]
    
    def __str__(self):
        emoji = dict(self.ALERT_LEVELS).get(self.alert_level, '')
        return f"{emoji} {self.pasajero.nombre_completo} → {self.destino} ({self.checked_at.strftime('%Y-%m-%d')})"
    
    def get_alert_emoji(self):
        """Retorna el emoji correspondiente al nivel de alerta"""
        return dict(self.ALERT_LEVELS).get(self.alert_level, '⚪')
    
    def get_transit_display(self):
        """Retorna los tránsitos en formato legible"""
        if not self.transitos:
            return "Sin escalas"
        return " → ".join(self.transitos)
    
    def is_recent(self, days=7):
        """Verifica si la validación es reciente (útil para cache)"""
        return (timezone.now() - self.checked_at).days <= days

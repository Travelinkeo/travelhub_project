"""Modelo de Cruceros para TravelHub"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class CruceroReserva(models.Model):
    """Reserva de Crucero con itinerario, cabina y paquetes adicionales"""
    
    id_crucero = models.AutoField(primary_key=True, verbose_name=_("ID Crucero"))
    venta = models.ForeignKey('Venta', related_name='cruceros', on_delete=models.CASCADE, 
                             verbose_name=_('Venta'))
    
    # === INFORMACIÓN GENERAL ===
    nombre_crucero = models.CharField(_('Nombre del Crucero'), max_length=200,
                                     help_text=_('Ej: Caribbean Explorer 7 Noches'))
    naviera = models.CharField(_('Naviera/Compañía'), max_length=150,
                              help_text=_('Ej: Royal Caribbean, Carnival, MSC'))
    nombre_barco = models.CharField(_('Nombre del Barco'), max_length=150, blank=True)
    
    # === FECHAS ===
    fecha_embarque = models.DateField(_('Fecha de Embarque'))
    fecha_desembarque = models.DateField(_('Fecha de Desembarque'))
    noches = models.PositiveSmallIntegerField(_('Noches'), 
                                             help_text=_('Número de noches a bordo'))
    
    # === ITINERARIO ===
    puerto_embarque = models.CharField(_('Puerto de Embarque'), max_length=150)
    puerto_desembarque = models.CharField(_('Puerto de Desembarque'), max_length=150)
    puertos_escala = models.JSONField(_('Puertos de Escala'), blank=True, null=True,
                                     help_text=_('Lista de puertos: [{"puerto": "Cozumel", "dia": 2, "actividades": "..."}]'))
    dias_navegacion = models.PositiveSmallIntegerField(_('Días de Navegación'), default=0,
                                                       help_text=_('Días en alta mar sin puerto'))
    
    # === CABINA/CAMAROTE ===
    class TipoCabina(models.TextChoices):
        INTERIOR = 'INT', _('Interior (sin ventana)')
        VENTANA = 'VEN', _('Vista al Mar (con ventana)')
        BALCON = 'BAL', _('Balcón Privado')
        SUITE = 'SUI', _('Suite')
        SUITE_PREMIUM = 'SUP', _('Suite Premium')
    
    tipo_cabina = models.CharField(_('Tipo de Cabina'), max_length=3, 
                                  choices=TipoCabina.choices, default=TipoCabina.BALCON)
    numero_cabina = models.CharField(_('Número de Cabina'), max_length=20, blank=True)
    ubicacion_cabina = models.CharField(_('Ubicación en el Barco'), max_length=100, blank=True,
                                       help_text=_('Ej: Deck 8, Proa, Popa'))
    clase_cabina = models.CharField(_('Clase de Cabina'), max_length=50, blank=True,
                                   help_text=_('Ej: Deluxe, Premium, Concierge'))
    
    # === PASAJEROS ===
    numero_pasajeros = models.PositiveSmallIntegerField(_('Número de Pasajeros'), default=2)
    nombres_pasajeros = models.TextField(_('Nombres de Pasajeros'),
                                        help_text=_('Uno por línea o separados por coma'))
    
    # === PAQUETES ADICIONALES ===
    paquete_bebidas = models.BooleanField(_('Paquete de Bebidas'), default=False)
    tipo_paquete_bebidas = models.CharField(_('Tipo Paquete Bebidas'), max_length=100, blank=True,
                                           help_text=_('Ej: Refrescos, Clásico, Premium, Deluxe'))
    costo_paquete_bebidas = models.DecimalField(_('Costo Paquete Bebidas'), max_digits=10, 
                                                decimal_places=2, blank=True, null=True)
    
    paquete_restaurantes = models.BooleanField(_('Paquete Restaurantes Especialidad'), default=False)
    detalle_restaurantes = models.TextField(_('Detalle Restaurantes'), blank=True,
                                           help_text=_('Restaurantes incluidos y menús'))
    costo_paquete_restaurantes = models.DecimalField(_('Costo Paquete Restaurantes'), 
                                                     max_digits=10, decimal_places=2, 
                                                     blank=True, null=True)
    
    paquete_spa = models.BooleanField(_('Paquete Spa y Bienestar'), default=False)
    detalle_spa = models.TextField(_('Detalle Spa'), blank=True,
                                  help_text=_('Tratamientos incluidos'))
    costo_paquete_spa = models.DecimalField(_('Costo Paquete Spa'), max_digits=10, 
                                           decimal_places=2, blank=True, null=True)
    
    paquete_wifi = models.BooleanField(_('Paquete Wi-Fi'), default=False)
    tipo_paquete_wifi = models.CharField(_('Tipo Paquete Wi-Fi'), max_length=100, blank=True,
                                        help_text=_('Ej: Básico, Premium, Streaming'))
    costo_paquete_wifi = models.DecimalField(_('Costo Paquete Wi-Fi'), max_digits=10, 
                                            decimal_places=2, blank=True, null=True)
    
    excursiones_tierra = models.JSONField(_('Excursiones en Tierra'), blank=True, null=True,
                                         help_text=_('Lista de excursiones contratadas por puerto'))
    
    # === PENSIÓN Y SERVICIOS INCLUIDOS ===
    pension_completa = models.BooleanField(_('Pensión Completa Incluida'), default=True)
    servicios_incluidos = models.TextField(_('Servicios Incluidos'), blank=True,
                                          help_text=_('Detalle de lo que incluye la tarifa base'))
    servicios_no_incluidos = models.TextField(_('Servicios NO Incluidos'), blank=True,
                                             help_text=_('Ej: Propinas, bebidas alcohólicas, excursiones'))
    
    # === PROVEEDOR Y COSTOS ===
    proveedor = models.ForeignKey('core.Proveedor', on_delete=models.SET_NULL, 
                                  blank=True, null=True, verbose_name=_('Proveedor/Consolidador'))
    localizador_proveedor = models.CharField(_('Localizador Proveedor'), max_length=100, blank=True)
    
    tarifa_base_cabina = models.DecimalField(_('Tarifa Base Cabina'), max_digits=12, 
                                            decimal_places=2, blank=True, null=True,
                                            help_text=_('Costo base de la cabina'))
    
    es_comisionable = models.BooleanField(_('Es Comisionable'), default=True,
                                         help_text=_('Si el proveedor paga comisión'))
    porcentaje_comision = models.DecimalField(_('% Comisión'), max_digits=5, decimal_places=2, 
                                             blank=True, null=True,
                                             help_text=_('Porcentaje de comisión del proveedor'))
    monto_comision = models.DecimalField(_('Monto Comisión'), max_digits=12, decimal_places=2,
                                        blank=True, null=True, editable=False,
                                        help_text=_('Calculado automáticamente'))
    
    fee_servicio_agencia = models.DecimalField(_('Fee Servicio Agencia'), max_digits=12, 
                                              decimal_places=2, blank=True, null=True,
                                              help_text=_('Fee que cobra la agencia al cliente'))
    
    costo_total_proveedor = models.DecimalField(_('Costo Total Proveedor'), max_digits=12, 
                                               decimal_places=2, blank=True, null=True,
                                               help_text=_('Total a pagar al proveedor'))
    precio_venta_cliente = models.DecimalField(_('Precio Venta Cliente'), max_digits=12, 
                                              decimal_places=2, blank=True, null=True,
                                              help_text=_('Total que paga el cliente'))
    
    # === MONEDA ===
    moneda = models.ForeignKey('core.Moneda', on_delete=models.PROTECT, 
                              verbose_name=_('Moneda'))
    
    # === NOTAS ===
    observaciones = models.TextField(_('Observaciones'), blank=True,
                                    help_text=_('Notas internas sobre la reserva'))
    recomendaciones_cliente = models.TextField(_('Recomendaciones al Cliente'), blank=True,
                                              help_text=_('Consejos sobre roaming, propinas, etc.'))
    
    class Meta:
        verbose_name = _('Crucero')
        verbose_name_plural = _('Cruceros')
        ordering = ['fecha_embarque']
    
    def __str__(self):
        return f"{self.nombre_crucero} - {self.fecha_embarque}"
    
    def save(self, *args, **kwargs):
        # Calcular comisión si es comisionable
        if self.es_comisionable and self.tarifa_base_cabina and self.porcentaje_comision:
            self.monto_comision = self.tarifa_base_cabina * (self.porcentaje_comision / 100)
        
        super().save(*args, **kwargs)
    
    @property
    def margen_neto(self):
        """Margen neto de la agencia"""
        if self.precio_venta_cliente and self.costo_total_proveedor:
            comision = self.monto_comision or Decimal('0.00')
            fee = self.fee_servicio_agencia or Decimal('0.00')
            return comision + fee
        return None
    
    @property
    def margen_porcentaje(self):
        """Porcentaje de margen sobre precio de venta"""
        if self.margen_neto and self.precio_venta_cliente and self.precio_venta_cliente > 0:
            return (self.margen_neto / self.precio_venta_cliente) * 100
        return None

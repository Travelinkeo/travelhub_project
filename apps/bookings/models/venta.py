from __future__ import annotations
import uuid
import logging
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Sum

from core.models.base import AgenciaMixin, SoftDeleteModel
from apps.finance.models.currencies import Moneda
from .servicios import ProductoServicio, Proveedor

logger = logging.getLogger(__name__)

class Venta(SoftDeleteModel, AgenciaMixin, models.Model):
    """
    🏢 MULTI-TENANT
    Modelo Maestro (El Sol del ERP): Single Source of Truth para todas las reservas y flujos de caja.
    """
    id_venta = models.AutoField(primary_key=True, verbose_name=_("ID Venta/Reserva"))
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True, verbose_name=_("Token Público"))
    localizador = models.CharField(_("Localizador/PNR"), max_length=20, blank=True, help_text=_("Código único de la reserva o localizador."))
    
    cliente = models.ForeignKey('crm.Cliente', on_delete=models.PROTECT, related_name='ventas_asociadas', verbose_name=_("Cliente (Pagador)"), null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings_ventas_creadas', verbose_name=_("Creado Por"))
    pasajeros = models.ManyToManyField('crm.Pasajero', related_name='bookings_ventas', verbose_name=_("Pasajeros"))
    
    cotizacion_origen = models.OneToOneField('cotizaciones.Cotizacion', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Cotización de Origen"))
    fecha_venta = models.DateTimeField(_("Fecha de Venta/Reserva"), default=timezone.now)
    descripcion_general = models.TextField(_("Descripción General de la Venta"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"), null=True, blank=True)
    tasa_cambio_bcv = models.DecimalField(_("Tasa de Cambio (BCV)"), max_digits=12, decimal_places=4, default=1, help_text=_("Tasa oficial BCV para la fecha de venta."))
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(_("Impuestos"), max_digits=12, decimal_places=2, default=0)
    total_venta = models.DecimalField(_("Total Venta"), max_digits=12, decimal_places=2, default=0, editable=False)
    monto_pagado = models.DecimalField(_("Monto Pagado"), max_digits=12, decimal_places=2, default=0)
    saldo_pendiente = models.DecimalField(_("Saldo Pendiente"), max_digits=12, decimal_places=2, default=0, editable=False)

    class EstadoVenta(models.TextChoices):
        PENDIENTE_PAGO = 'PEN', _('Pendiente de Pago')
        PAGADA_PARCIAL = 'PAR', _('Pagada Parcialmente')
        PAGADA_TOTAL = 'PAG', _('Pagada Totalmente')
        CONFIRMADA = 'CNF', _('Confirmada (Servicios OK)')
        EN_PROCESO_VIAJE = 'VIA', _('En Proceso/Viaje')
        COMPLETADA = 'COM', _('Completada')
        FALLIDA = 'FAL', _('Falla de Sistema (Revertida)')
        CANCELADA = 'CAN', _('Cancelada')
    estado = models.CharField(_("Estado de la Venta/Reserva"), max_length=3, choices=EstadoVenta.choices, default=EstadoVenta.PENDIENTE_PAGO)

    class TipoVenta(models.TextChoices):
        B2C = 'B2C', _('B2C (Ocio)')
        B2B = 'B2B', _('B2B (Corporativo)')
        MICE = 'MICE', _('MICE / Eventos')
        PAQUETE = 'PKG', _('Paquete')
        CIRCUITO = 'CIR', _('Circuito')
        TAILOR = 'TLD', _('Viaje a Medida')
        SEGURO = 'SEG', _('Solo Seguro')
        OTRO = 'OTR', _('Otro')
    tipo_venta = models.CharField(_("Tipo de Venta"), max_length=4, choices=TipoVenta.choices, default=TipoVenta.B2C, db_index=True)

    class CanalOrigen(models.TextChoices):
        ADMIN = 'ADM', _('Admin')
        IMPORTACION = 'IMP', _('Importación')
        API = 'API', _('API')
        WEBFORM = 'WEB', _('Formulario Web')
        MIGRACION = 'MIG', _('Migración')
        OTRO = 'OTR', _('Otro')
    canal_origen = models.CharField(_("Canal de Origen"), max_length=3, choices=CanalOrigen.choices, default=CanalOrigen.ADMIN, db_index=True)

    margen_estimado = models.DecimalField(_("Margen Estimado"), max_digits=12, decimal_places=2, blank=True, null=True, help_text=_("Precio venta - costo neto estimado (informativo)."))
    co2_estimado_kg = models.DecimalField(_("Emisiones CO₂ Estimadas (kg)"), max_digits=12, decimal_places=2, blank=True, null=True, help_text=_("Estimación agregada de la huella de carbono."))
    asiento_contable_venta = models.ForeignKey('contabilidad.AsientoContable', related_name='bookings_ventas_asociadas', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Asiento Contable de Venta"))
    factura = models.ForeignKey('finance.Factura', on_delete=models.SET_NULL, blank=True, null=True, related_name='bookings_ventas', verbose_name=_("Factura Asociada (Legacy)"))
    factura_consolidada = models.ForeignKey('finance.FacturaConsolidada', on_delete=models.SET_NULL, blank=True, null=True, related_name='bookings_ventas_facturadas', verbose_name=_("Factura Consolidada"))
    notas = models.TextField(_("Notas de la Venta"), blank=True, null=True)
    puntos_fidelidad_asignados = models.BooleanField(_("Puntos Fidelidad Asignados"), default=False, editable=False, help_text=_("Evita otorgar puntos duplicados cuando la venta pasa a completada/pagada."))
    
    ultima_vista_cliente = models.DateTimeField(_("Última Vista Cliente"), blank=True, null=True)
    contador_vistas_cliente = models.PositiveIntegerField(_("Contador de Vistas"), default=0)
    
    def registrar_vista_cliente(self):
        self.ultima_vista_cliente = timezone.now()
        self.contador_vistas_cliente += 1
        self.save(update_fields=['ultima_vista_cliente', 'contador_vistas_cliente'])

    def get_status_badge(self):
        colors = {
            self.EstadoVenta.PENDIENTE_PAGO: "bg-amber-900/40 text-amber-400 border border-amber-700/50",
            self.EstadoVenta.PAGADA_PARCIAL: "bg-blue-900/40 text-blue-400 border border-blue-700/50",
            self.EstadoVenta.PAGADA_TOTAL: "bg-emerald-900/40 text-emerald-400 border border-emerald-700/50",
            self.EstadoVenta.CONFIRMADA: "bg-indigo-900/40 text-indigo-400 border border-indigo-700/50",
            self.EstadoVenta.EN_PROCESO_VIAJE: "bg-purple-900/40 text-purple-400 border border-purple-700/50",
            self.EstadoVenta.COMPLETADA: "bg-gray-700 text-gray-300",
            self.EstadoVenta.CANCELADA: "bg-rose-900/40 text-rose-400 border border-rose-700/50",
        }
        return colors.get(self.estado, "bg-gray-700 text-gray-300")

    class Meta:
        verbose_name = _("Venta/Reserva")
        verbose_name_plural = _("Ventas/Reservas")
        ordering = ['-fecha_venta']
        db_table = 'core_venta'
        indexes = [
            models.Index(fields=['agencia', 'fecha_venta']),
            models.Index(fields=['agencia', 'localizador']),
            models.Index(fields=['agencia', 'estado']),
        ]

    def __str__(self):
        try:
             cliente_str = str(self.cliente)
        except Exception:
             cliente_str = "Cliente Desconocido/Borrado"
        return f"Venta {self.localizador or self.id_venta} a {cliente_str}"

    def save(self, *args, **kwargs):
        if not self.localizador:
            self.localizador = f"VTA-{self.fecha_venta.strftime('%Y%m%d')}-{Venta.objects.count() + 1:04d}"
        
        if not self.pk:
            self.total_venta = (self.subtotal or 0) + (self.impuestos or 0)
            self.saldo_pendiente = self.total_venta - (self.monto_pagado or 0)
        
        super().save(*args, **kwargs)

    def _evaluar_otorgar_puntos(self, contexto: str):
        try:
            if self.cliente and not self.puntos_fidelidad_asignados and (self.saldo_pendiente <= 0 or self.estado in (Venta.EstadoVenta.COMPLETADA, Venta.EstadoVenta.PAGADA_TOTAL)):
                puntos_ganados = int(self.total_venta / 10)
                if puntos_ganados > 0:
                    self.cliente.puntos_fidelidad += puntos_ganados
                    self.cliente.calcular_cliente_frecuente()
                    self.cliente.save(update_fields=['puntos_fidelidad', 'es_cliente_frecuente'])
                    self.puntos_fidelidad_asignados = True
                    super().save(update_fields=['puntos_fidelidad_asignados'])
        except Exception:
            logger.exception("Error otorgando puntos en Venta %s.", self.pk)

    def recalcular_finanzas(self):
        # Ahora sumamos desde ItemVenta que es el registro central
        subtotal_items = Decimal('0.00')
        impuestos_items = Decimal('0.00')
        
        items = self.items_venta.all()
        for item in items:
            subtotal_items += item.subtotal_item_venta
            impuestos_items += (item.impuestos_item_venta * item.cantidad)
            
        fees_total = self.fees_venta.aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'fees_venta') else Decimal('0.00')
        pagos_confirmados = self.pagos_venta.filter(confirmado=True).aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'pagos_venta') else Decimal('0.00')
        
        self.subtotal = subtotal_items
        self.impuestos = impuestos_items
        self.total_venta = subtotal_items + impuestos_items + fees_total
        self.monto_pagado = pagos_confirmados
        self.saldo_pendiente = self.total_venta - self.monto_pagado
        campos_update = ['subtotal', 'impuestos', 'total_venta', 'monto_pagado', 'saldo_pendiente']
        estado_original = self.estado
        estados_financieros_base = {Venta.EstadoVenta.PENDIENTE_PAGO, Venta.EstadoVenta.PAGADA_PARCIAL, Venta.EstadoVenta.PAGADA_TOTAL}
        if self.estado in estados_financieros_base and self.total_venta > 0:
            if self.saldo_pendiente <= 0:
                self.estado = Venta.EstadoVenta.PAGADA_TOTAL
            elif 0 < self.saldo_pendiente < self.total_venta:
                self.estado = Venta.EstadoVenta.PAGADA_PARCIAL
        if self.estado != estado_original:
            campos_update.append('estado')
        super().save(update_fields=campos_update)
        self._evaluar_otorgar_puntos(contexto="recalcular_finanzas")

    def delete(self, using=None, keep_parents=False, force=False):
        """Lógica de validación antes de borrar (Soft Delete se hereda)."""
        if not force:
            componentes_relacionados = {
                'items_venta': self.items_venta.exists(), 
                'segmentos_vuelo': self.segmentos_vuelo.exists(), 
                'alojamientos': self.alojamientos.exists(), 
                'traslados': self.traslados.exists(), 
                'actividades': self.actividades.exists(), 
                'fees_venta': self.fees_venta.exists(), 
                'pagos_venta': self.pagos_venta.exists()
            }
            bloqueados = [n for n, ex in componentes_relacionados.items() if ex]
            if bloqueados:
                raise ValidationError(_(f"No se puede eliminar la Venta porque existen componentes asociados: {', '.join(bloqueados)}"))
            
        # Si llegamos aquí, aplicamos el borrado (que será Soft por defecto gracias a AgenciaMixin/SoftDeleteModel)
        return super().delete(using=using, keep_parents=keep_parents, force=force)

    def _latest_metadata(self):
        try:
            return self.metadata_parseo.first()
        except Exception:
            return None

    @property
    def total_fees(self):
        return self.fees_venta.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')

    @property
    def amount_consistency(self):
        md = self._latest_metadata()
        return md.amount_consistency if md else None

    @property
    def amount_difference(self):
        md = self._latest_metadata()
        return str(md.amount_difference) if md and md.amount_difference is not None else None

    @property
    def taxes_amount_expected(self):
        md = self._latest_metadata()
        return str(md.taxes_amount_expected) if md and md.taxes_amount_expected is not None else None

    @property
    def taxes_difference(self):
        md = self._latest_metadata()
        return str(md.taxes_difference) if md and md.taxes_difference is not None else None


class ItemVenta(SoftDeleteModel, AgenciaMixin, models.Model):
    """
    Entidad polimórfica que detalla cada línea atómica/Stock vendido.
    """
    id_item_venta = models.AutoField(primary_key=True, verbose_name=_("ID Item Venta"))
    venta = models.ForeignKey(Venta, related_name='items_venta', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    producto_servicio = models.ForeignKey(ProductoServicio, on_delete=models.PROTECT, verbose_name=_("Producto/Servicio"), null=True, blank=True)
    descripcion_personalizada = models.CharField(_("Descripción Personalizada"), max_length=500, blank=True, null=True)
    cantidad = models.PositiveIntegerField(_("Cantidad"), default=1)
    precio_unitario_venta = models.DecimalField(_("Precio Unitario de Venta"), max_digits=12, decimal_places=2)
    costo_unitario_referencial = models.DecimalField(_("Costo Unitario Referencial"), max_digits=12, decimal_places=2, blank=True, null=True)
    impuestos_item_venta = models.DecimalField(_("Impuestos por Item"), max_digits=12, decimal_places=2, default=0)
    subtotal_item_venta = models.DecimalField(_("Subtotal Item"), max_digits=12, decimal_places=2, editable=False)
    total_item_venta = models.DecimalField(_("Total Item"), max_digits=12, decimal_places=2, editable=False)
    fecha_inicio_servicio = models.DateTimeField(_("Fecha Inicio Servicio"), blank=True, null=True)
    fecha_fin_servicio = models.DateTimeField(_("Fecha Fin Servicio"), blank=True, null=True)
    codigo_reserva_proveedor = models.CharField(_("Código Reserva Proveedor (PNR, Localizador)"), max_length=50, blank=True, null=True)
    proveedor_servicio = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor del Servicio"))

    costo_neto_proveedor = models.DecimalField(_("Costo Neto Proveedor"), max_digits=12, decimal_places=2, blank=True, null=True)
    fee_proveedor = models.DecimalField(_("Fee Emisión Proveedor"), max_digits=12, decimal_places=2, blank=True, null=True)
    comision_agencia_monto = models.DecimalField(_("Comisión Agencia (Monto)"), max_digits=12, decimal_places=2, blank=True, null=True)
    fee_agencia_interno = models.DecimalField(_("Fee Interno Agencia"), max_digits=12, decimal_places=2, blank=True, null=True)
    
    tipo_item = models.CharField(
        _("Tipo de Item"), 
        max_length=3, 
        choices=ProductoServicio.TipoProductoChoices.choices, 
        default=ProductoServicio.TipoProductoChoices.OTRO
    )
    detalles_json = models.JSONField(_("Detalles Específicos (JSON)"), blank=True, null=True, help_text=_("Metadatos adicionales del producto (Hotel, Auto, etc.)"))

    class EstadoItemVenta(models.TextChoices):
        PENDIENTE_CONFIRMACION = 'PCO', _('Pendiente Confirmación Proveedor')
        CONFIRMADO = 'CNF', _('Confirmado por Proveedor')
        CANCELADO_PROVEEDOR = 'CAP', _('Cancelado por Proveedor')
        CANCELADO_CLIENTE = 'CAC', _('Cancelado por Cliente')
        UTILIZADO = 'UTI', _('Utilizado/Completado')
    estado_item = models.CharField(_("Estado del Item/Servicio"), max_length=3, choices=EstadoItemVenta.choices, default=EstadoItemVenta.PENDIENTE_CONFIRMACION)
    notas_item = models.TextField(_("Notas del Item"), blank=True, null=True)

    class Meta:
        verbose_name = _("Item de Venta/Reserva")
        verbose_name_plural = _("Items de Venta/Reserva")
        db_table = 'core_itemventa'

    def __str__(self):
        return f"{self.cantidad} x {self.producto_servicio.nombre if self.producto_servicio else 'Producto'} en Venta {self.venta.localizador if self.venta else 'N/A'}"

    def save(self, *args, **kwargs):
        self.subtotal_item_venta = self.precio_unitario_venta * self.cantidad
        self.total_item_venta = self.subtotal_item_venta + (self.impuestos_item_venta * self.cantidad)
        super().save(*args, **kwargs)

class VentaParseMetadata(AgenciaMixin, models.Model):
    id_metadata = models.AutoField(primary_key=True, verbose_name=_("ID Metadata Parseo"))
    venta = models.ForeignKey(Venta, related_name='metadata_parseo', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    fuente = models.CharField(_("Fuente / Origen"), max_length=50, blank=True, null=True, help_text=_("Ej: SABRE, KIU, AMADEUS, IMPORT_MANUAL"))
    currency = models.CharField(_("Moneda"), max_length=10, blank=True, null=True)
    fare_amount = models.DecimalField(_("Monto Fare"), max_digits=12, decimal_places=2, blank=True, null=True)
    taxes_amount = models.DecimalField(_("Monto Taxes Detectado"), max_digits=12, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(_("Monto Total"), max_digits=12, decimal_places=2, blank=True, null=True)
    amount_consistency = models.CharField(_("Consistencia Montos"), max_length=15, blank=True, null=True)
    amount_difference = models.DecimalField(_("Diferencia Total vs Fare+Taxes"), max_digits=12, decimal_places=2, blank=True, null=True)
    taxes_amount_expected = models.DecimalField(_("Taxes Esperados (Total - Fare)"), max_digits=12, decimal_places=2, blank=True, null=True)
    taxes_difference = models.DecimalField(_("Diferencia Taxes Detectado vs Esperado"), max_digits=12, decimal_places=2, blank=True, null=True)
    segments_json = models.JSONField(_("Segmentos (JSON)"), blank=True, null=True, help_text=_("Lista de segmentos normalizados."))
    raw_normalized_json = models.JSONField(_("Objeto Normalized Completo"), blank=True, null=True, help_text=_("Bloque normalized completo para auditoría."))
    creado = models.DateTimeField(_("Creado"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Metadata de Parseo de Venta")
        verbose_name_plural = _("Metadata de Parseo de Ventas")
        ordering = ['-creado']
        db_table = 'core_ventaparsemetadata'

    def __str__(self):
        return f"Metadata Parseo Venta {self.venta_id} {self.fuente or ''} {self.creado:%Y-%m-%d %H:%M:%S}".strip()

class VentaAuditFinding(AgenciaMixin, models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='audit_findings', verbose_name=_("Venta/Reserva"), null=True, blank=True)
    
    class FindingType(models.TextChoices):
        CRITICAL_ZERO_SALE = 'CZS', _('Venta con Total 0')
        MISSING_COSTS = 'MSC', _('Costos No Registrados')
        NEGATIVE_MARGIN = 'NMG', _('Margen Negativo')
        GDS_ERP_DISCREPANCY = 'GED', _('Discrepancia GDS vs ERP')
        OTHER = 'OTH', _('Otro Hallazgo')
        
    tipo = models.CharField(_("Tipo de Hallazgo"), max_length=3, choices=FindingType.choices)
    mensaje = models.TextField(_("Descripción del Hallazgo"))
    
    class FindingStatus(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente')
        REVISADO = 'REV', _('Revisado')
        IGNORADO = 'IGN', _('Ignorado')
        SOLUCIONADO = 'SOL', _('Solucionado')
        
    estado = models.CharField(_("Estado"), max_length=3, choices=FindingStatus.choices, default=FindingStatus.PENDIENTE)
    fecha_deteccion = models.DateTimeField(_("Fecha de Detección"), auto_now_add=True)
    
    es_hallazgo_valido = models.BooleanField(_("¿Es Hallazgo Válido?"), null=True, blank=True, help_text="Permite entrenar a la IA sobre falsos positivos.")
    nota_resolucion = models.TextField(_("Nota de Resolución"), null=True, blank=True)
    fecha_resolucion = models.DateTimeField(_("Fecha de Resolución"), null=True, blank=True)
    resuelto_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Resuelto por"))
    
    class Meta:
        verbose_name = _("Hallazgo de Auditoría")
        verbose_name_plural = _("Hallazgos de Auditoría")
        ordering = ['-fecha_deteccion']
        db_table = 'bookings_ventaauditfinding'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.venta.localizador if self.venta else 'N/A'} ({self.get_estado_display()})"

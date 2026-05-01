"""Modelos de Ventas / Reservas y componentes (Refactor apps.bookings).

Fase de modularización: Migrado desde `core/models/ventas.py`.
Incluye:
  - Venta e ItemVenta
  - Componentes de viaje (AlojamientoReserva, TrasladoServicio, ActividadServicio, SegmentoVuelo)
  - Fees y Pagos
  - Componentes adicionales
  - Metadata de parseo
  - Auditoría
"""

from __future__ import annotations

import datetime
from core.models.base import AgenciaMixin
import logging
import uuid
import hashlib
import json as _json
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone as _tz
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.middleware import get_current_request_meta
from core.models.audit import AuditLog, crear_audit_log as _crear_audit_log
# REFACTOR: Usar referencias lazy para evitar importaciones circulares con core.models
# (AsientoContable se usará como string 'core.AsientoContable' en los campos)
from core.models_catalogos import Ciudad, Moneda, ProductoServicio, Proveedor

# REFACTOR: Importaciones desde apps.crm (Usar strings 'crm.Cliente' y 'crm.Pasajero' en modelos)
# from apps.crm.models import Cliente, Pasajero 

from core.mixins import SoftDeleteModel

logger = logging.getLogger(__name__)

# --- Venta y componentes ---

class Venta(SoftDeleteModel, AgenciaMixin, models.Model):
    """
    🚨 CRÍTICO | 🏢 MULTI-TENANT
    Modelo Maestro (El Sol del ERP): Single Source of Truth para todas las reservas y flujos de caja.
    
    ¿Por qué?: Este modelo orquesta la totalidad del motor de negocios SaaS para las agencias inscritas.
    Todos los motores satélite (Generador de PDFs, Parseador IA, Comisiones, Tiempos HTMX) dependen 
    invariablemente del estado de este objeto en DB. Un fallo aquí, rompe el sistema completo.
    
    # 🏢 SEGURIDAD MULTI-TENANT: 
    # El campo `agencia` es el escudo primario. Todo QuerySet expuesto vía UI/API DEBE usar el `TenantManager` 
    # internamente o filtrar explícitamente (`.filter(agencia=req.user.agencia)`) para impedir fugas catastróficas 
    # de PNRs/Clientes entre agencias competidoras.
    """
    id_venta = models.AutoField(primary_key=True, verbose_name=_("ID Venta/Reserva"))
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True, verbose_name=_("Token Público"))
    localizador = models.CharField(_("Localizador/PNR"), max_length=20, blank=True, help_text=_("Código único de la reserva o localizador."))
    
    # REFACTOR: Usar strings por estabilidad
    cliente = models.ForeignKey('crm.Cliente', on_delete=models.PROTECT, related_name='ventas_asociadas', verbose_name=_("Cliente (Pagador)"), null=True, blank=True)
    # agencia la provee AgenciaMixin de forma automatizada
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
    factura_consolidada = models.ForeignKey('core.FacturaConsolidada', on_delete=models.SET_NULL, blank=True, null=True, related_name='bookings_ventas_facturadas', verbose_name=_("Factura Consolidada"))
    notas = models.TextField(_("Notas de la Venta"), blank=True, null=True)
    puntos_fidelidad_asignados = models.BooleanField(_("Puntos Fidelidad Asignados"), default=False, editable=False, help_text=_("Evita otorgar puntos duplicados cuando la venta pasa a completada/pagada."))
    
    # Tracking & Analytics (Phase 2 Upgrade)
    ultima_vista_cliente = models.DateTimeField(_("Última Vista Cliente"), blank=True, null=True)
    contador_vistas_cliente = models.PositiveIntegerField(_("Contador de Vistas"), default=0)
    
    def registrar_vista_cliente(self):
        self.ultima_vista_cliente = timezone.now()
        self.contador_vistas_cliente += 1
        self.save(update_fields=['ultima_vista_cliente', 'contador_vistas_cliente'])

    def get_status_badge(self):
        """Retorna las clases de Tailwind para el badge de estado de la venta."""
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

    # objects y all_objects los provee AgenciaMixin de forma automatizada

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

    def __str__(self):  # pragma: no cover
        try:
             cliente_str = str(self.cliente)
        except Exception:
             cliente_str = "Cliente Desconocido/Borrado"
        return f"Venta {self.localizador or self.id_venta} a {cliente_str}"

    def save(self, *args, **kwargs):
        # Generar localizador si no existe
        if not self.localizador:
            self.localizador = f"VTA-{self.fecha_venta.strftime('%Y%m%d')}-{Venta.objects.count() + 1:04d}"
        
        # Calcular totales básicos
        if not self.pk:  # Solo en creación
            self.total_venta = (self.subtotal or 0) + (self.impuestos or 0)
            self.saldo_pendiente = self.total_venta - (self.monto_pagado or 0)
        
        super().save(*args, **kwargs)

    def _evaluar_otorgar_puntos(self, contexto: str):  # pragma: no cover
        try:
            logger.debug("[Venta %s] Evaluación puntos (%s): estado=%s total=%s saldo=%s flag=%s", self.pk, contexto, self.estado, self.total_venta, self.saldo_pendiente, self.puntos_fidelidad_asignados)
            if self.cliente and not self.puntos_fidelidad_asignados and (self.saldo_pendiente <= 0 or self.estado in (Venta.EstadoVenta.COMPLETADA, Venta.EstadoVenta.PAGADA_TOTAL)):
                puntos_ganados = int(self.total_venta / 10)
                if puntos_ganados > 0:
                    self.cliente.puntos_fidelidad += puntos_ganados
                    self.cliente.calcular_cliente_frecuente()
                    self.cliente.save(update_fields=['puntos_fidelidad', 'es_cliente_frecuente'])
                    self.puntos_fidelidad_asignados = True
                    super().save(update_fields=['puntos_fidelidad_asignados'])
        except Exception:
            try:
                cli_str = str(self.cliente)
            except:
                cli_str = "Error Retrieving Cliente"
            logger.exception("Error otorgando puntos en Venta %s. Cliente: %s", self.pk, cli_str)

    def recalcular_finanzas(self):  # pragma: no cover (copia literal)
        """
        🚨 CRÍTICO
        Motor Aritmético: Re-evalúa el subtotal, total e impuestos de la venta basado recursivamente en la sumatoria de sus hijos.
        
        ¿Por qué Top-Down Sum?: Las agencias agregan "Fees" post-venta o cancelan Items parciales 
        (ej: "El pasajero va, pero canceló el hotel de escala"). La tabla Venta queda desfasada con facilidad.
        Este método engrosa el Saldo Pendiente de forma idempotente, resguardando la cuenta contable (Cuentas por Cobrar).
        """
        subtotal_items = sum(iv.total_item_venta for iv in self.items_venta.all()) if self.items_venta.exists() else Decimal('0.00')
        fees_total = self.fees_venta.aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'fees_venta') else Decimal('0.00')
        pagos_confirmados = self.pagos_venta.filter(confirmado=True).aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'pagos_venta') else Decimal('0.00')
        self.subtotal = subtotal_items
        self.total_venta = subtotal_items + (self.impuestos or 0) + fees_total
        self.monto_pagado = pagos_confirmados
        self.saldo_pendiente = self.total_venta - self.monto_pagado
        campos_update = ['subtotal', 'total_venta', 'monto_pagado', 'saldo_pendiente']
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

    def delete(self, using=None, keep_parents=False, force=False):  # pragma: no cover
        """
        Borrado de Venta. 
        Por defecto es borrado lógico (Soft Delete) y verifica componentes.
        Si force=True, realiza borrado físico (Hard Delete).
        """
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
            
            # Borrado lógico (vía SoftDeleteModel)
            return super().delete(using=using, keep_parents=keep_parents)
        
        # Borrado físico real (Bypass checks and cascading via DB if configured)
        # Nota: La mayoría de las FKs en apps.bookings están como CASCADE.
        return self.hard_delete(using=using, keep_parents=keep_parents)

    def _latest_metadata(self):  # pragma: no cover
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
    🚨 CRÍTICO
    Entidad polimórfica que detalla cada línea atómica/Stock vendido.
    
    ¿Por qué aislar Items separándolos de Venta?: El "Patrón de Modularidad GDS". 
    Un Boleto capturado en TXT/Sabre puede detonar que un solo "PNR" tenga múltiples items: 
    Vuelo + Asiento Premium + Maleta Extra 2PC. Cada uno sufre un "Mark-Up" (Fee Proveedor vs Agencia Interna) separado. 
    Es inviable acoplar estos costos granulares en un campo plano heredado de `Venta`.
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

    # Campos para costos y rentabilidad
    costo_neto_proveedor = models.DecimalField(_("Costo Neto Proveedor"), max_digits=12, decimal_places=2, blank=True, null=True)
    fee_proveedor = models.DecimalField(_("Fee Emisión Proveedor"), max_digits=12, decimal_places=2, blank=True, null=True)
    comision_agencia_monto = models.DecimalField(_("Comisión Agencia (Monto)"), max_digits=12, decimal_places=2, blank=True, null=True)
    fee_agencia_interno = models.DecimalField(_("Fee Interno Agencia"), max_digits=12, decimal_places=2, blank=True, null=True)

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
        return f"{self.cantidad} x {self.producto_servicio.nombre} en Venta {self.venta.localizador}"

    def save(self, *args, **kwargs):
        # Calcular totales
        self.subtotal_item_venta = self.precio_unitario_venta * self.cantidad
        self.total_item_venta = self.subtotal_item_venta + (self.impuestos_item_venta * self.cantidad)
        super().save(*args, **kwargs)


class AlojamientoReserva(AgenciaMixin, models.Model):
    id_alojamiento_reserva = models.AutoField(primary_key=True, verbose_name=_('ID Alojamiento'))
    venta = models.ForeignKey(Venta, related_name='alojamientos', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    item_venta = models.ForeignKey(ItemVenta, related_name='alojamientos_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
    nombre_establecimiento = models.CharField(_('Nombre Establecimiento'), max_length=150)
    check_in = models.DateField(_('Check In'), blank=True, null=True)
    check_out = models.DateField(_('Check Out'), blank=True, null=True)
    regimen_alimentacion = models.CharField(_('Régimen Alimentación'), max_length=30, blank=True, null=True, help_text=_('Ej: Desayuno, Media Pensión, Todo Incluido'))
    habitaciones = models.PositiveSmallIntegerField(_('Habitaciones'), default=1)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, verbose_name=_('Ciudad'), null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Proveedor'))
    nombre_pasajero = models.CharField(_('Nombre Pasajero'), max_length=255, blank=True)
    localizador_proveedor = models.CharField(_('Localizador Proveedor'), max_length=100, blank=True)
    notas = models.TextField(_('Notas'), blank=True, null=True)

    class Meta:
        verbose_name = _('Alojamiento (Reserva)')
        verbose_name_plural = _('Alojamientos (Reservas)')
        ordering = ['check_in']
        db_table = 'core_alojamientoreserva'

    def __str__(self):
        return f"{self.nombre_establecimiento} ({self.check_in or ''})"


class TrasladoServicio(AgenciaMixin, models.Model):
    id_traslado_servicio = models.AutoField(primary_key=True, verbose_name=_('ID Traslado'))
    venta = models.ForeignKey(Venta, related_name='traslados', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)

    class TipoTraslado(models.TextChoices):
        ARRIBO = 'ARR', _('Arribo / Llegada')
        SALIDA = 'DEP', _('Salida')
        INTERNO = 'INT', _('Interno')
    tipo_traslado = models.CharField(_('Tipo Traslado'), max_length=3, choices=TipoTraslado.choices, default=TipoTraslado.ARRIBO)
    origen = models.CharField(_('Origen'), max_length=150, blank=True, null=True)
    destino = models.CharField(_('Destino'), max_length=150, blank=True, null=True)
    fecha_hora = models.DateTimeField(_('Fecha/Hora'), blank=True, null=True)
    pasajeros = models.PositiveSmallIntegerField(_('Pasajeros'), default=1)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Proveedor'))
    notas = models.TextField(_('Notas'), blank=True, null=True)

    class Meta:
        verbose_name = _('Traslado')
        verbose_name_plural = _('Traslados')
        ordering = ['fecha_hora']
        db_table = 'core_trasladoservicio'

    def __str__(self):
        return f"Traslado {self.origen or ''}->{self.destino or ''} {self.fecha_hora or ''}".strip()


class ActividadServicio(AgenciaMixin, models.Model):
    id_actividad_servicio = models.AutoField(primary_key=True, verbose_name=_('ID Actividad'))
    venta = models.ForeignKey(Venta, related_name='actividades', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    nombre = models.CharField(_('Nombre Actividad'), max_length=150)
    fecha = models.DateField(_('Fecha'), blank=True, null=True)
    duracion_horas = models.DecimalField(_('Duración (horas)'), max_digits=5, decimal_places=2, blank=True, null=True)
    incluye = models.TextField(_('Incluye'), blank=True, null=True)
    no_incluye = models.TextField(_('No Incluye'), blank=True, null=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Proveedor'))
    nombre_pasajero = models.CharField(_('Nombre Pasajero'), max_length=255, blank=True)
    localizador_proveedor = models.CharField(_('Localizador Proveedor'), max_length=100, blank=True)
    notas = models.TextField(_('Notas'), blank=True, null=True)

    class Meta:
        verbose_name = _('Actividad / Excursión')
        verbose_name_plural = _('Actividades / Excursiones')
        ordering = ['fecha', 'nombre']
        db_table = 'core_actividadservicio'

    def __str__(self):
        return self.nombre


class SegmentoVuelo(AgenciaMixin, models.Model):
    id_segmento_vuelo = models.AutoField(primary_key=True, verbose_name=_('ID Segmento Vuelo'))
    venta = models.ForeignKey(Venta, related_name='segmentos_vuelo', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    origen = models.ForeignKey(Ciudad, related_name='bookings_segmentos_salida', on_delete=models.PROTECT, verbose_name=_('Ciudad Origen'), null=True, blank=True)
    destino = models.ForeignKey(Ciudad, related_name='bookings_segmentos_llegada', on_delete=models.PROTECT, verbose_name=_('Ciudad Destino'), null=True, blank=True)
    aerolinea = models.CharField(_('Aerolínea'), max_length=80, blank=True, null=True)
    numero_vuelo = models.CharField(_('Número de Vuelo'), max_length=20, blank=True, null=True)
    fecha_salida = models.DateTimeField(_('Fecha/Hora Salida'), blank=True, null=True)
    fecha_llegada = models.DateTimeField(_('Fecha/Hora Llegada'), blank=True, null=True)
    clase_reserva = models.CharField(_('Clase'), max_length=5, blank=True, null=True)
    cabina = models.CharField(_('Cabina'), max_length=20, blank=True, null=True, help_text=_('Ej: Economy, Business, First'))
    notas = models.TextField(_('Notas'), blank=True, null=True)

    class Meta:
        verbose_name = _('Segmento de Vuelo')
        verbose_name_plural = _('Segmentos de Vuelo')
        ordering = ['fecha_salida']
        db_table = 'core_segmentovuelo'

    def __str__(self):
        return f"{self.origen} → {self.destino} {self.numero_vuelo or ''}".strip()


class FeeVenta(AgenciaMixin, models.Model):
    id_fee_venta = models.AutoField(primary_key=True, verbose_name=_("ID Fee"))
    venta = models.ForeignKey(Venta, related_name='fees_venta', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)

    class TipoFee(models.TextChoices):
        EMISION = 'EMI', _('Emisión')
        CAMBIO = 'CAM', _('Cambio / Exchange')
        GESTION = 'GST', _('Gestión')
        URGENTE = 'URG', _('Urgente')
        OTRO = 'OTR', _('Otro')
    tipo_fee = models.CharField(_("Tipo Fee"), max_length=3, choices=TipoFee.choices, default=TipoFee.GESTION)
    descripcion = models.CharField(_("Descripción"), max_length=200, blank=True, null=True)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"), null=True, blank=True)
    es_comision_agencia = models.BooleanField(_("Es Comisión Agencia"), default=True)
    taxable = models.BooleanField(_("Sujeto a Impuestos"), default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Fee de Venta")
        verbose_name_plural = _("Fees de Venta")
        ordering = ['-creado']
        db_table = 'core_feeventa'

    def __str__(self):
        return f"{self.get_tipo_fee_display()} {self.monto} {self.moneda.codigo_iso}"


class PagoVenta(AgenciaMixin, models.Model):
    """
    🚨 CRÍTICO
    Append-Only Ledger: Registro legal de ingresos abonados a la cuenta por cobrar de una Venta.
    
    ¿Por qué este diseño?: Se rige por la Convención Contable de ERPs. 
    Una vez que se asocia un pago (Transferencia Confirmada, Zelle, Pasarela Stripe), 
    NO ESTÁ PENSADO PARA BORRARSE SILENCIOSAMENTE (`SoftDeleteModel` excluido adrede para esto). 
    Si hay fraudes o "bounces", el flujo dicta crear un movimiento "Negativo" reflejando la anulación, 
    sin destruir el Row original para mantener impecable la Auditoría Financiera.
    """
    id_pago_venta = models.AutoField(primary_key=True, verbose_name=_("ID Pago"))
    venta = models.ForeignKey(Venta, related_name='pagos_venta', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    fecha_pago = models.DateTimeField(_("Fecha Pago"), default=timezone.now)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"), null=True, blank=True)

    class MetodoPago(models.TextChoices):
        EFECTIVO = 'EFE', _('Efectivo')
        TARJETA = 'TAR', _('Tarjeta')
        TRANSFERENCIA = 'TRF', _('Transferencia')
        ZELLE = 'ZEL', _('Zelle')
        PAYPAL = 'PPL', _('PayPal')
        OTRO = 'OTR', _('Otro')
    metodo = models.CharField(_("Método"), max_length=3, choices=MetodoPago.choices, default=MetodoPago.TRANSFERENCIA)
    referencia = models.CharField(_("Referencia"), max_length=100, blank=True, null=True)
    confirmado = models.BooleanField(_("Confirmado"), default=True)
    
    # IGTF Fields
    aplica_igtf = models.BooleanField(_("Aplica IGTF (3%)"), default=False, help_text=_("Impuesto a Grandes Transacciones Financieras (Divisas)"))
    tasa_igtf = models.DecimalField(_("Tasa IGTF %"), max_digits=5, decimal_places=2, default=3.00)
    monto_igtf = models.DecimalField(_("Monto IGTF"), max_digits=12, decimal_places=2, default=0)

    notas = models.TextField(_("Notas"), blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Pago de Venta")
        verbose_name_plural = _("Pagos de Venta")
        ordering = ['-fecha_pago']
        db_table = 'core_pagoventa'

    def __str__(self):
        return f"Pago {self.monto} {self.moneda.codigo_iso} ({self.get_metodo_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-calc IGTF if flag is true
        if self.aplica_igtf and self.monto:
            self.monto_igtf = self.monto * (self.tasa_igtf / 100)
        else:
            self.monto_igtf = 0
        super().save(*args, **kwargs)

    @property
    def total_con_igtf(self):
        return (self.monto or 0) + (self.monto_igtf or 0)


class AlquilerAutoReserva(AgenciaMixin, models.Model):
    id_alquiler_auto = models.AutoField(primary_key=True, verbose_name=_("ID Alquiler Auto"))
    venta = models.ForeignKey(Venta, related_name='alquileres_autos', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor"))
    ciudad_retiro = models.ForeignKey(Ciudad, related_name='bookings_autos_retiro', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad Retiro"))
    ciudad_devolucion = models.ForeignKey(Ciudad, related_name='bookings_autos_devolucion', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad Devolución"))
    fecha_hora_retiro = models.DateTimeField(_("Fecha/Hora Retiro"), blank=True, null=True)
    fecha_hora_devolucion = models.DateTimeField(_("Fecha/Hora Devolución"), blank=True, null=True)
    categoria_auto = models.CharField(_("Categoría / Clase"), max_length=50, blank=True, null=True)
    compania_rentadora = models.CharField(_("Compañía Rentadora"), max_length=100, blank=True, null=True)
    numero_confirmacion = models.CharField(_("Número Confirmación"), max_length=100, blank=True, null=True)
    nombre_conductor = models.CharField(_("Nombre Conductor"), max_length=255, blank=True)
    incluye_seguro = models.BooleanField(_("Incluye Seguro"), default=False)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    costo_neto = models.DecimalField(_("Costo Neto"), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta = models.DecimalField(_("Precio Venta"), max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Alquiler de Auto")
        verbose_name_plural = _("Alquileres de Autos")
        ordering = ['fecha_hora_retiro']
        indexes = [models.Index(fields=['fecha_hora_retiro']), models.Index(fields=['fecha_hora_devolucion']), models.Index(fields=['compania_rentadora'])]
        db_table = 'core_alquilerautoreserva'

    def __str__(self):
        return f"Auto {self.categoria_auto or ''} {self.numero_confirmacion or ''}".strip()

    def clean(self):
        if self.fecha_hora_retiro and self.fecha_hora_devolucion and self.fecha_hora_devolucion < self.fecha_hora_retiro:
            raise ValidationError({'fecha_hora_devolucion': _("La fecha/hora de devolución no puede ser anterior al retiro.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def margen_amount(self):
        if self.precio_venta is not None and self.costo_neto is not None:
            return self.precio_venta - self.costo_neto
        return None

    @property
    def margen_pct(self):
        if self.margen_amount is not None and self.precio_venta not in (None, 0):
            try:
                return (self.margen_amount / self.precio_venta) * 100
            except Exception:
                return None
        return None


class EventoServicio(AgenciaMixin, models.Model):
    id_evento_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Evento/Servicio"))
    venta = models.ForeignKey(Venta, related_name='eventos_servicios', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor"))
    nombre_evento = models.CharField(_("Nombre Evento"), max_length=255)
    fecha_evento = models.DateTimeField(_("Fecha Evento"), blank=True, null=True)
    ubicacion = models.CharField(_("Ubicación"), max_length=255, blank=True, null=True)
    zona_asiento = models.CharField(_("Zona/Asiento"), max_length=100, blank=True, null=True)
    codigo_boleto_evento = models.CharField(_("Código Boleto / Ref"), max_length=100, blank=True, null=True)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    costo_neto = models.DecimalField(_("Costo Neto"), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta = models.DecimalField(_("Precio Venta"), max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Evento / Servicio")
        verbose_name_plural = _("Eventos / Servicios")
        ordering = ['fecha_evento']
        indexes = [models.Index(fields=['fecha_evento']), models.Index(fields=['nombre_evento'])]
        db_table = 'core_eventoservicio'

    def __str__(self):
        return f"Evento {self.nombre_evento}"

    @property
    def margen_amount(self):
        if self.precio_venta is not None and self.costo_neto is not None:
            return self.precio_venta - self.costo_neto
        return None

    @property
    def margen_pct(self):
        if self.margen_amount is not None and self.precio_venta not in (None, 0):
            try:
                return (self.margen_amount / self.precio_venta) * 100
            except Exception:
                return None
        return None


class CircuitoTuristico(AgenciaMixin, models.Model):
    id_circuito = models.AutoField(primary_key=True, verbose_name=_("ID Circuito"))
    venta = models.ForeignKey(Venta, related_name='circuitos_turisticos', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    nombre_circuito = models.CharField(_("Nombre Circuito"), max_length=255)
    dias_total = models.PositiveSmallIntegerField(_("Días Totales"), blank=True, null=True)
    fecha_inicio = models.DateField(_("Fecha Inicio"), blank=True, null=True)
    fecha_fin = models.DateField(_("Fecha Fin"), blank=True, null=True)
    descripcion_general = models.TextField(_("Descripción General"), blank=True, null=True)
    incluye = models.TextField(_("Incluye"), blank=True, null=True)
    no_incluye = models.TextField(_("No Incluye"), blank=True, null=True)
    costo_neto_estimado = models.DecimalField(_("Costo Neto Estimado"), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta_estimado = models.DecimalField(_("Precio Venta Estimado"), max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Circuito Turístico")
        verbose_name_plural = _("Circuitos Turísticos")
        ordering = ['-fecha_inicio']
        indexes = [models.Index(fields=['fecha_inicio'])]
        db_table = 'core_circuitoturistico'

    def __str__(self):
        return self.nombre_circuito

    def _recalcular_dias_total(self):
        max_dia = self.dias.aggregate(models.Max('dia_numero'))['dia_numero__max'] or 0
        if max_dia and self.dias_total != max_dia:
            self.dias_total = max_dia
        return self.dias_total

    def _recalcular_fecha_fin(self):
        if self.fecha_inicio and self.dias_total:
            derivada = self.fecha_inicio + datetime.timedelta(days=self.dias_total - 1)
            if self.fecha_fin != derivada:
                self.fecha_fin = derivada
        return self.fecha_fin

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.dias_total:
            diff = (self.fecha_fin - self.fecha_inicio).days + 1
            if diff != self.dias_total:
                raise ValidationError({'dias_total': _("dias_total no coincide con el rango de fechas ({} días).".format(diff))})
        if self.dias_total is not None and self.dias_total <= 0:
            raise ValidationError({'dias_total': _("dias_total debe ser > 0")})

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.pk:
            if self.fecha_inicio and self.dias_total and not self.fecha_fin:
                self._recalcular_fecha_fin()
        else:
            if self.fecha_inicio and self.dias_total and not self.fecha_fin:
                self._recalcular_fecha_fin()
        super().save(*args, **kwargs)

    @property
    def margen_amount(self):
        if self.precio_venta_estimado is not None and self.costo_neto_estimado is not None:
            return self.precio_venta_estimado - self.costo_neto
        return None

    @property
    def margen_pct(self):
        if self.margen_amount is not None and self.precio_venta_estimado not in (None, 0):
            try:
                return (self.margen_amount / self.precio_venta_estimado) * 100
            except Exception:
                return None
        return None


class CircuitoDia(models.Model):
    id_circuito_dia = models.AutoField(primary_key=True, verbose_name=_("ID Circuito Día"))
    circuito = models.ForeignKey(CircuitoTuristico, related_name='dias', on_delete=models.CASCADE, verbose_name=_("Circuito"), null=True, blank=True)
    dia_numero = models.PositiveSmallIntegerField(_("Día #"))
    titulo = models.CharField(_("Título del Día"), max_length=255, blank=True, null=True)
    descripcion = models.TextField(_("Descripción"), blank=True, null=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad"))
    alojamiento_previsto = models.CharField(_("Alojamiento Previsto"), max_length=255, blank=True, null=True)
    actividades_resumen = models.TextField(_("Actividades/Resumen"), blank=True, null=True)

    class Meta:
        verbose_name = _("Día de Circuito")
        verbose_name_plural = _("Días de Circuito")
        ordering = ['circuito', 'dia_numero']
        unique_together = ('circuito', 'dia_numero')
        indexes = [models.Index(fields=['dia_numero'])]
        db_table = 'core_circuitodia'

    def __str__(self):
        return f"{self.circuito.nombre_circuito} - Día {self.dia_numero}"

    def clean(self):
        if self.dia_numero <= 0:
            raise ValidationError({'dia_numero': _("El día debe ser > 0")})
        if self.circuito_id and self.circuito.dias_total and self.dia_numero > self.circuito.dias_total:
            pass

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


@receiver([post_save, post_delete], sender=CircuitoDia)
def actualizar_circuito_dias(sender, instance, **kwargs):  # pragma: no cover
    circuito = instance.circuito
    max_dia = circuito.dias.aggregate(models.Max('dia_numero'))['dia_numero__max'] or 0
    if max_dia:
        circuito.dias_total = max_dia
        if circuito.fecha_inicio:
            circuito.fecha_fin = circuito.fecha_inicio + datetime.timedelta(days=max_dia - 1)
    else:
        circuito.dias_total = None
        circuito.fecha_fin = None
    circuito.save(update_fields=['dias_total', 'fecha_fin'])


class PaqueteAereo(AgenciaMixin, models.Model):
    id_paquete_aereo = models.AutoField(primary_key=True, verbose_name=_("ID Paquete Aéreo"))
    venta = models.ForeignKey(Venta, related_name='paquetes_aereos', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    nombre_paquete = models.CharField(_("Nombre Paquete"), max_length=255, blank=True, null=True)
    incluye_vuelos = models.BooleanField(_("Incluye Vuelos"), default=True)
    incluye_hotel = models.BooleanField(_("Incluye Hotel"), default=False)
    noches = models.PositiveSmallIntegerField(_("Noches"), blank=True, null=True)
    pasajeros = models.PositiveSmallIntegerField(_("Pasajeros"), blank=True, null=True)
    resumen_componentes = models.JSONField(_("Resumen Componentes"), blank=True, null=True, help_text=_("Estructura agregada de vuelos/hoteles/otros."))
    observaciones = models.TextField(_("Observaciones"), blank=True, null=True)
    costo_neto_estimado = models.DecimalField(_("Costo Neto Estimado"), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta_estimado = models.DecimalField(_("Precio Venta Estimado"), max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Paquete Aéreo")
        verbose_name_plural = _("Paquetes Aéreos")
        ordering = ['-id_paquete_aereo']
        indexes = [models.Index(fields=['incluye_vuelos', 'incluye_hotel'])]
        db_table = 'core_paqueteaereo'

    def __str__(self):
        return self.nombre_paquete or f"Paquete Aéreo {self.id_paquete_aereo}"

    def clean(self):
        super().clean()
        if self.resumen_componentes is not None:
            if not isinstance(self.resumen_componentes, dict):
                raise ValidationError({'resumen_componentes': _("Debe ser un objeto JSON (dict)")})
            allowed_top = {'flights', 'hotels', 'extras'}
            unknown = set(self.resumen_componentes.keys()) - allowed_top
            if unknown:
                raise ValidationError({'resumen_componentes': _("Claves no permitidas: {}".format(', '.join(sorted(unknown))))})
            for key in allowed_top:
                if key in self.resumen_componentes:
                    val = self.resumen_componentes[key]
                    if not isinstance(val, list):
                        raise ValidationError({f'resumen_componentes.{key}': _("Debe ser una lista")})
                    for idx, item in enumerate(val):
                        if not isinstance(item, dict):
                            raise ValidationError({f'resumen_componentes.{key}[{idx}]': _("Cada elemento debe ser objeto")})
                        if key == 'flights':
                            for req in ['origin','destination']:
                                if req not in item:
                                    raise ValidationError({f'resumen_componentes.flights[{idx}]': _("Falta campo obligatorio '{}'".format(req))})
                        if key == 'hotels':
                            for req in ['name','nights']:
                                if req not in item:
                                    raise ValidationError({f'resumen_componentes.hotels[{idx}]': _("Falta campo obligatorio '{}'".format(req))})
                        if key == 'extras':
                            if len(item.keys()) > 10:
                                raise ValidationError({f'resumen_componentes.extras[{idx}]': _("Demasiados campos en elemento extra (máx 10)")})
            if self.incluye_hotel and 'hotels' in self.resumen_componentes:
                total_nights = 0
                for h in self.resumen_componentes.get('hotels', []):
                    try:
                        nights = int(h.get('nights', 0))
                    except (TypeError, ValueError) as e:
                        raise ValidationError({'resumen_componentes.hotels': _("'nights' debe ser entero")}) from e
                    if nights < 0:
                        raise ValidationError({'resumen_componentes.hotels': _("'nights' no puede ser negativo")})
                    total_nights += nights
                if self.noches and total_nights and total_nights != self.noches:
                    raise ValidationError({'noches': _("El total de nights en hotels ({}) no coincide con campo noches ({}).".format(total_nights, self.noches))})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def margen_amount(self):
        if self.precio_venta_estimado is not None and self.costo_neto_estimado is not None:
            return self.precio_venta_estimado - self.costo_neto
        return None

    @property
    def margen_pct(self):
        if self.margen_amount is not None and self.precio_venta_estimado not in (None, 0):
            try:
                return (self.margen_amount / self.precio_venta_estimado) * 100
            except Exception:
                return None
        return None


class ServicioAdicionalDetalle(AgenciaMixin, models.Model):
    class TipoServicioChoices(models.TextChoices):
        SEGURO = 'SEG', _('Seguro')
        SIM = 'SIM', _('SIM / E-SIM')
        ASISTENCIA = 'AST', _('Asistencia')
        LOUNGE = 'LNG', _('Lounge')
        FASTTRACK = 'FST', _('Fast Track')
        OTRO = 'OTR', _('Otro')
    id_servicio_adicional = models.AutoField(primary_key=True, verbose_name=_("ID Servicio Adicional"))
    venta = models.ForeignKey(Venta, related_name='servicios_adicionales', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor"))
    tipo_servicio = models.CharField(_("Tipo Servicio"), max_length=3, choices=TipoServicioChoices.choices, default=TipoServicioChoices.OTRO)
    descripcion = models.CharField(_("Descripción"), max_length=255, blank=True, null=True)
    codigo_referencia = models.CharField(_("Código Referencia"), max_length=100, blank=True, null=True)
    fecha_inicio = models.DateField(_("Fecha Inicio"), blank=True, null=True)
    fecha_fin = models.DateField(_("Fecha Fin"), blank=True, null=True)
    nombre_pasajero = models.CharField(_("Nombre Pasajero"), max_length=150, blank=True, null=True)
    pasaporte_pasajero = models.CharField(_("Pasaporte Pasajero"), max_length=50, blank=True, null=True)
    detalles_cobertura = models.TextField(_("Detalles Cobertura"), blank=True, null=True)
    contacto_emergencia = models.TextField(_("Contacto Emergencia"), blank=True, null=True)
    participantes = models.CharField(_("Participantes"), max_length=100, blank=True, null=True)
    operado_por = models.CharField(_("Operado Por"), max_length=150, blank=True, null=True)
    hora_lugar_encuentro = models.CharField(_("Hora y Lugar de Encuentro"), max_length=255, blank=True, null=True)
    duracion_estimada = models.CharField(_("Duración Estimada"), max_length=100, blank=True, null=True)
    inclusiones_servicio = models.TextField(_("Inclusiones Servicio"), blank=True, null=True)
    recomendaciones = models.TextField(_("Recomendaciones"), blank=True, null=True)
    metadata_json = models.JSONField(_("Metadata Adicional"), blank=True, null=True)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    costo_neto = models.DecimalField(_("Costo Neto"), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta = models.DecimalField(_("Precio Venta"), max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Servicio Adicional Detalle")
        verbose_name_plural = _("Servicios Adicionales Detalle")
        ordering = ['-id_servicio_adicional']
        indexes = [models.Index(fields=['tipo_servicio'])]
        db_table = 'core_servicioadicionaldetalle'

    def __str__(self):
        return f"Servicio {self.tipo_servicio} {self.codigo_referencia or ''}".strip()

    @property
    def margen_amount(self):
        if self.precio_venta is not None and self.costo_neto is not None:
            return self.precio_venta - self.costo_neto
        return None

    @property
    def margen_pct(self):
        if self.margen_amount is not None and self.precio_venta not in (None, 0):
            try:
                return (self.margen_amount / self.precio_venta) * 100
            except Exception:
                return None
        return None


class VentaParseMetadata(models.Model):
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


# AuditLog movido a core/models/audit.py para blindaje centralizado.


from core.validators import antivirus_hook, validate_file_extension, validate_file_size
from core.utils_storage import truncate_filename
from core.storage import RawFileStorage

class BoletoImportado(SoftDeleteModel, AgenciaMixin, models.Model):
    id_boleto_importado = models.AutoField(primary_key=True, verbose_name=_("ID Boleto Importado"))
    archivo_boleto = models.FileField(
        _("Archivo del Boleto (.pdf, .txt, .eml)"),
        upload_to='boletos_importados/%Y/%m/',
        max_length=255,
        help_text=_("Suba el archivo del boleto en formato PDF, TXT o EML (máx 5MB)."),
        validators=[validate_file_size, validate_file_extension, antivirus_hook],
        blank=True, null=True,
        storage=RawFileStorage
    )
    fecha_subida = models.DateTimeField(_("Fecha de Subida"), auto_now_add=True)
    # agencia la provee AgenciaMixin
    
    class FormatoDetectado(models.TextChoices):
        PDF_KIU = 'PDF_KIU', _('PDF (KIU)')
        PDF_SABRE = 'PDF_SAB', _('PDF (Sabre)')
        PDF_AMADEUS = 'PDF_AMA', _('PDF (Amadeus)')
        TXT_KIU = 'TXT_KIU', _('TXT (KIU)')
        TXT_SABRE = 'TXT_SAB', _('TXT (Sabre)')
        TXT_AMADEUS = 'TXT_AMA', _('TXT (Amadeus)')
        EML_KIU = 'EML_KIU', _('EML (KIU)') 
        EML_GENERAL = 'EML_GEN', _('EML (General)')
        OTRO = 'OTR', _('Otro/Desconocido')
        ERROR_FORMATO = 'ERR', _('Error de Formato')

    formato_detectado = models.CharField(
        _("Formato Detectado"),
        max_length=20,
        choices=FormatoDetectado.choices,
        default=FormatoDetectado.OTRO,
        blank=True
    )
    
    datos_parseados = models.JSONField(_("Datos Parseados"), blank=True, null=True, help_text=_("Información extraída del boleto en formato JSON."))
    
    class EstadoParseo(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente de Parseo')
        EN_PROCESO = 'PRO', _('En Proceso')
        COMPLETADO = 'COM', _('Parseo Completado')
        REVISION_REQUERIDA = 'REV', _('Revisión Requerida')
        ERROR_PARSEO = 'ERR', _('Error en Parseo')
        NO_APLICA = 'NAP', _('No Aplica Parseo')
        COLA_LLENA = 'QUE', _('Pendiente (Cola Llena)')

    estado_parseo = models.CharField(
        _("Estado del Parseo"),
        max_length=3,
        choices=EstadoParseo.choices,
        default=EstadoParseo.PENDIENTE,
    )
    log_parseo = models.TextField(_("Log del Parseo"), blank=True, null=True)
    
    numero_boleto = models.CharField(_("Número de Boleto"), max_length=50, blank=True, null=True)
    nombre_pasajero_completo = models.CharField(_("Nombre Completo Pasajero (Original)"), max_length=150, blank=True, null=True)
    nombre_pasajero_procesado = models.CharField(_("Nombre Pasajero (Procesado)"), max_length=150, blank=True, null=True)
    ruta_vuelo = models.TextField(_("Ruta del Vuelo (Itinerario)"), blank=True, null=True) 
    fecha_emision_boleto = models.DateField(_("Fecha de Emisión del Boleto"), blank=True, null=True)
    aerolinea_emisora = models.CharField(_("Aerolínea Emisora"), max_length=200, blank=True, null=True)
    direccion_aerolinea = models.TextField(_("Dirección Aerolínea"), blank=True, null=True)
    agente_emisor = models.CharField(_("Agente Emisor"), max_length=200, blank=True, null=True)
    foid_pasajero = models.CharField(_("FOID/D.Identidad Pasajero"), max_length=50, blank=True, null=True)
    localizador_pnr = models.CharField(_("Localizador (PNR)"), max_length=20, blank=True, null=True)
    tarifa_base = models.DecimalField(_("Tarifa Base"), max_digits=10, decimal_places=2, blank=True, null=True)
    impuestos_descripcion = models.TextField(_("Descripción Impuestos"), blank=True, null=True)
    impuestos_total_calculado = models.DecimalField(_("Total Impuestos (Calculado)"), max_digits=10, decimal_places=2, blank=True, null=True)
    total_boleto = models.DecimalField(_("Total del Boleto"), max_digits=10, decimal_places=2, blank=True, null=True)
    exchange_monto = models.DecimalField(_("Exchange"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Monto de exchange o diferencial de cambio asociado al boleto."))
    void_monto = models.DecimalField(_("Void / Penalidad"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Monto asociado a VOID (penalidad / reembolso negativo)."))
    comision_agencia = models.DecimalField(_("Comisión Agencia"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Comisión propia de la agencia respecto al boleto."))
    
    iva_monto = models.DecimalField(_("Monto IVA"), max_digits=10, decimal_places=2, blank=True, null=True)
    inatur_monto = models.DecimalField(_("Monto Inatur (1%)"), max_digits=10, decimal_places=2, blank=True, null=True)
    otros_impuestos_monto = models.DecimalField(_("Otros Impuestos"), max_digits=10, decimal_places=2, blank=True, null=True)
    fee_servicio = models.DecimalField(_("Fee de Servicio"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Fee cobrado por la agencia por gestión del boleto."))
    igtf_monto = models.DecimalField(_("IGTF"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Impuesto a las Grandes Transacciones Financieras u otras retenciones locales."))
    
    proveedor_emisor = models.ForeignKey('core.Proveedor', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Proveedor Emisor (Consolidador/Aerolínea)"))
    
    venta_asociada = models.ForeignKey(
        'Venta', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='boletos_adjuntos', 
        verbose_name=_("Venta/Reserva Asociada")
    )
    
    archivo_pdf_generado = models.FileField(
        _("PDF Unificado Generado"),
        upload_to='boletos_generados/%Y/%m/',
        max_length=255,
        blank=True, null=True,
        help_text=_("El archivo PDF del boleto unificado, generado automáticamente."),
        storage=RawFileStorage
    )

    telegram_file_id = models.CharField(
        _("Telegram File ID"),
        max_length=255,
        blank=True, null=True,
        help_text=_("ID del archivo en la nube de Telegram (para almacenamiento gratuito).")
    )

    version = models.PositiveIntegerField(_("Versión"), default=1, help_text=_("Versión del boleto (1=Original, 2+=Re-emisión)"))
    
    boleto_padre = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='versiones_posteriores',
        verbose_name=_("Boleto Padre (Versión Anterior)")
    )

    class EstadoEmision(models.TextChoices):
        ORIGINAL = 'ORI', _('Original')
        REEMISION = 'REE', _('Re-emisión')
        ANULADO = 'ANU', _('Anulado / Void')
        REEMBOLSO = 'REM', _('Reembolso')

    estado_emision = models.CharField(
        _("Estado de Emisión"),
        max_length=3,
        choices=EstadoEmision.choices,
        default=EstadoEmision.ORIGINAL
    )

    # objects y all_objects los provee AgenciaMixin automatizadamente

    class Meta:
        verbose_name = _("Boleto Importado")
        verbose_name_plural = _("Boletos Importados")
        ordering = ['-fecha_subida']
        db_table = 'core_boletoimportado'
        indexes = [
            models.Index(fields=['agencia', 'numero_boleto']),
            models.Index(fields=['agencia', 'localizador_pnr']),
            models.Index(fields=['agencia', 'fecha_subida']),
            models.Index(fields=['agencia', 'localizador_pnr', 'fecha_subida']),
        ]

    def __str__(self):
        return f"Boleto {self.id_boleto_importado} ({self.archivo_boleto.name if self.archivo_boleto else 'N/A'})"

    def get_pdf_url(self):
        """Devuelve la URL del PDF unificado si existe, sino None."""
        if self.archivo_pdf_generado:
            try:
                return self.archivo_pdf_generado.url
            except Exception:
                return None
        return None


class SolicitudAnulacion(AgenciaMixin, models.Model):
    id_anulacion = models.AutoField(primary_key=True, verbose_name=_("ID Anulación"))
    boleto = models.ForeignKey(BoletoImportado, on_delete=models.CASCADE, related_name='solicitudes_anulacion', verbose_name=_("Boleto"), null=True, blank=True)
    
    class TipoAnulacion(models.TextChoices):
        VOLUNTARIA = 'VOL', _('Voluntaria')
        INVOLUNTARIA = 'INV', _('Involuntaria')
        CAMBIO = 'CAM', _('Cambio de Itinerario')
        OTRO = 'OTR', _('Otro')
    tipo_anulacion = models.CharField(_("Tipo Anulación"), max_length=3, choices=TipoAnulacion.choices, default=TipoAnulacion.VOLUNTARIA)
    
    motivo = models.TextField(_("Motivo"))
    monto_original = models.DecimalField(_("Monto Original"), max_digits=12, decimal_places=2)
    penalidad_aerolinea = models.DecimalField(_("Penalidad Aerolínea"), max_digits=12, decimal_places=2, default=0)
    fee_agencia = models.DecimalField(_("Fee Agencia"), max_digits=12, decimal_places=2, default=0)
    monto_reembolso = models.DecimalField(_("Monto a Reembolsar"), max_digits=12, decimal_places=2)
    
    class EstadoSolicitud(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente')
        APROBADA = 'APR', _('Aprobada')
        RECHAZADA = 'REC', _('Rechazada')
        PROCESADA = 'PRO', _('Procesada')
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoSolicitud.choices, default=EstadoSolicitud.PENDIENTE)
    
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Solicitado Por"))
    fecha_solicitud = models.DateTimeField(_("Fecha Solicitud"), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_("Fecha Actualización"), auto_now=True)
    
    class Meta:
        verbose_name = _("Solicitud de Anulación")
        verbose_name_plural = _("Solicitudes de Anulación")
        ordering = ['-fecha_solicitud']
        db_table = 'core_solicitudanulacion'

    def __str__(self):
        return f"Anulación {self.id_anulacion} - Boleto {self.id_anulacion}"


@receiver(post_save, sender=BoletoImportado)
def signal_boleto_post_save(sender, instance, created, **kwargs):
    """
    DISPARADOR DE TAX REFUND:
    Al terminar el procesamiento exitoso del boleto, encolamos el análisis 
    de recupero de impuestos.
    """
    if instance.estado_parseo == 'COM': 
        # 1. Disparar Tax Refund (DESACTIVADO TEMPORALMENTE PARA EVITAR 502)
        # try:
        #      from apps.finance.tasks_tax_refund import evaluar_tax_refund_task
        #      evaluar_tax_refund_task.delay(instance.pk)
        # except (ImportError, Exception) as e:
        #      logger.error(f"Error disparando Tax Refund: {e}")

        # 2. WORKFLOW MÁGICO: Automatización de Venta
        # NOTA: La creación de venta ahora es orquestada EXCLUSIVAMENTE por TicketParserService
        # para evitar duplicidad de procesos y asegurar la integridad de los datos.
        pass
# Auditoría forense trasladada a core/signals_audit.py


@receiver(post_save, sender=PagoVenta)
def signal_pago_post_save(sender, instance, created, **kwargs):  # pragma: no cover
    if instance.venta:
        instance.venta.recalcular_finanzas()
        
        # --- AGREGAR CONTABILIDAD DE PAGO ---
        if instance.confirmado:
            try:
                from apps.contabilidad.services import ContabilidadService
                ContabilidadService.registrar_pago_y_diferencial(instance)
            except Exception as e:
                logger.error(f"Error en contabilidad del pago {instance.pk}: {e}")

        if instance.venta.pk:
             instance.venta._evaluar_otorgar_puntos(contexto="signal_pago_post_save")

@receiver(post_delete, sender=PagoVenta)
def signal_pago_post_delete(sender, instance, **kwargs):  # pragma: no cover
    try:
        if instance.venta:
            instance.venta.recalcular_finanzas()
            if instance.venta.pk:
                instance.venta._evaluar_otorgar_puntos(contexto="signal_pago_post_save")
    except Exception:
        pass

@receiver(post_save, sender=Venta)
def enviar_email_confirmacion(sender, instance, created, **kwargs):
    """Envía email de confirmación cuando se crea una venta"""
    try:
        if created and instance.cliente and instance.cliente.email:
            # from core.services.email_service import enviar_confirmacion_venta
            # enviar_confirmacion_venta(instance)
            pass
    except Exception as e:
        logger.exception(f"Error enviando email confirmación para venta {instance.id_venta}: {e}")

@receiver(pre_save, sender=Venta)
def detectar_cambio_estado(sender, instance, **kwargs):
    """Detecta cambios de estado para enviar notificaciones"""
    if instance.pk:
        try:
            venta_anterior = Venta.objects.get(pk=instance.pk)
            if venta_anterior.estado != instance.estado:
                # Guardar estado anterior para usar en post_save
                instance._estado_anterior = venta_anterior.get_estado_display()
        except Venta.DoesNotExist:
            pass

@receiver(post_save, sender=Venta)
def enviar_email_cambio_estado(sender, instance, created, **kwargs):
    """Envía email cuando cambia el estado de una venta"""
    try:
        # 🔒 PROTECTED ACCESS: instance.cliente triggers query. Orphaned records raise DoesNotExist.
        if not created and hasattr(instance, '_estado_anterior') and instance.cliente and instance.cliente.email:
            try:
                # from core.services.email_service import enviar_cambio_estado
                # enviar_cambio_estado(instance, instance._estado_anterior)
                pass
            except Exception:
                # logger.exception(f"Error interno enviando email cambio estado venta {instance.id_venta}")
                pass
    except Exception as e:
        # Catch orphaned references or other access errors
        logger.warning(f"⚠️ Omitiendo email cambio estado para Venta {instance.pk}: {e}")

class VentaAuditFinding(AgenciaMixin, models.Model):
    """
    Persistencia de hallazgos del Revenue Leak AI.
    Permite el seguimiento de errores financieros detectados por la IA.
    """
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='audit_findings', verbose_name=_("Venta/Reserva"), null=True, blank=True)
    # agencia la provee AgenciaMixin
    
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
    
    # Feedback para RAG e IA
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
        return f"{self.get_tipo_display()} - {self.venta.localizador} ({self.get_estado_display()})"


# ==========================================
# 🚦 SEÑALES: AUTOMATIZACIÓN ASÍNCRONA
# ==========================================

@receiver(pre_save, sender=Venta)
def capturar_estado_anterior_venta(sender, instance, **kwargs):
    """
    Captura el estado actual en DB antes de guardar los cambios 
    para poder detectar transiciones de estado en el post_save.
    """
    if instance.pk:
        try:
            # Usamos all_objects para evitar filtros de agencia en este paso técnico
            obj_db = Venta.all_objects.get(pk=instance.pk)
            instance._estado_anterior = obj_db.estado
        except Venta.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Venta)
def disparar_notificacion_whatsapp_pago(sender, instance, created, **kwargs):
    """
    Gatillo asíncrono (Frente A): Si el estado cambia a 'PAG' (Pagada), 
    se encola la tarea de WhatsApp sin bloquear el hilo principal.
    """
    estado_anterior = getattr(instance, '_estado_anterior', None)
    estado_actual = instance.estado
    
    # Condición: El estado acaba de cambiar a PAGADA_TOTAL (PAG)
    # O se creó una venta directamente con estado PAG.
    recien_pagada = (estado_actual == Venta.EstadoVenta.PAGADA_TOTAL) and (estado_anterior != Venta.EstadoVenta.PAGADA_TOTAL)
    
    if recien_pagada:
        try:
            from .tasks import notificar_pago_whatsapp_task
            # Encolar en Celery (Carril de notificaciones configurado en travelhub/celery.py)
            notificar_pago_whatsapp_task.delay(instance.pk)
            logger.info(f"✅ [SIGNAL] Tarea de WhatsApp encolada para Venta {instance.pk}")
        except Exception as e:
            logger.error(f"❌ [SIGNAL] Error al intentar disparar notificación de WhatsApp: {e}")


"""Modelos de Ventas / Reservas y componentes (extraídos del monolítico).

Fase de modularización: el contenido proviene de `core/models.py` sin cambios
estructurales para evitar generar migraciones. Incluye:
  - Venta e ItemVenta
  - Componentes de viaje (AlojamientoReserva, TrasladoServicio, ActividadServicio, SegmentoVuelo)
  - Fees y Pagos (FeeVenta, PagoVenta)
  - Componentes adicionales (AlquilerAutoReserva, EventoServicio, CircuitoTuristico, CircuitoDia,
    PaqueteAereo, ServicioAdicionalDetalle)
  - Metadata de parseo de Venta (VentaParseMetadata)
  - Auditoría (AuditLog) + helpers / señales relacionadas

NOTA: Mantener sincronizado hasta retirar completamente el archivo legacy.
"""

from __future__ import annotations

import datetime
import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.middleware import get_current_request_meta
from core.models.contabilidad import AsientoContable
from core.models_catalogos import Ciudad, Moneda, ProductoServicio, Proveedor

logger = logging.getLogger(__name__)

# --- Venta y componentes ---

class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True, verbose_name=_("ID Venta/Reserva"))
    localizador = models.CharField(_("Localizador/PNR"), max_length=20, unique=True, blank=True, help_text=_("Código único de la reserva o localizador."))
    cliente = models.ForeignKey('personas.Cliente', on_delete=models.PROTECT, verbose_name=_("Cliente (Pagador)"), null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas_creadas', verbose_name=_("Creado Por"))
    pasajeros = models.ManyToManyField('personas.Pasajero', related_name='ventas', verbose_name=_("Pasajeros"))
    cotizacion_origen = models.OneToOneField('cotizaciones.Cotizacion', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Cotización de Origen"))
    fecha_venta = models.DateTimeField(_("Fecha de Venta/Reserva"), default=timezone.now)
    descripcion_general = models.TextField(_("Descripción General de la Venta"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
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
    asiento_contable_venta = models.ForeignKey(AsientoContable, related_name='ventas_asociadas', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Asiento Contable de Venta"))
    factura = models.ForeignKey('core.Factura', on_delete=models.SET_NULL, blank=True, null=True, related_name='ventas', verbose_name=_("Factura Asociada (Legacy)"))
    factura_consolidada = models.ForeignKey('core.FacturaConsolidada', on_delete=models.SET_NULL, blank=True, null=True, related_name='ventas_facturadas', verbose_name=_("Factura Consolidada"))
    notas = models.TextField(_("Notas de la Venta"), blank=True, null=True)
    puntos_fidelidad_asignados = models.BooleanField(_("Puntos Fidelidad Asignados"), default=False, editable=False, help_text=_("Evita otorgar puntos duplicados cuando la venta pasa a completada/pagada."))

    class Meta:
        verbose_name = _("Venta / Reserva")
        verbose_name_plural = _("Ventas / Reservas")
        ordering = ['-fecha_venta']

    def __str__(self):  # pragma: no cover
        return f"Venta {self.localizador or self.id_venta} a {self.cliente}"

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
            logger.exception("Error otorgando puntos en Venta %s. Cliente: %s", self.pk, self.cliente)

    def recalcular_finanzas(self):  # pragma: no cover (copia literal)
        from django.db.models import Sum
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

    def delete(self, using=None, keep_parents=False):  # pragma: no cover
        componentes_relacionados = {'items_venta': self.items_venta.exists(), 'segmentos_vuelo': self.segmentos_vuelo.exists(), 'alojamientos': self.alojamientos.exists(), 'traslados': self.traslados.exists(), 'actividades': self.actividades.exists(), 'fees_venta': self.fees_venta.exists(), 'pagos_venta': self.pagos_venta.exists()}
        bloqueados = [n for n, ex in componentes_relacionados.items() if ex]
        if bloqueados:
            raise ValidationError(_(f"No se puede eliminar la Venta porque existen componentes asociados: {', '.join(bloqueados)}"))
        return super().delete(using=using, keep_parents=keep_parents)

    def _latest_metadata(self):  # pragma: no cover
        try:
            return self.metadata_parseo.first()
        except Exception:
            return None

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


class ItemVenta(models.Model):
    id_item_venta = models.AutoField(primary_key=True, verbose_name=_("ID Item Venta"))
    venta = models.ForeignKey(Venta, related_name='items_venta', on_delete=models.CASCADE, verbose_name=_("Venta"))
    producto_servicio = models.ForeignKey(ProductoServicio, on_delete=models.PROTECT, verbose_name=_("Producto/Servicio"))
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

    def __str__(self):
        return f"{self.cantidad} x {self.producto_servicio.nombre} en Venta {self.venta.localizador}"

    def save(self, *args, **kwargs):
        # Calcular totales
        self.subtotal_item_venta = self.precio_unitario_venta * self.cantidad
        self.total_item_venta = self.subtotal_item_venta + (self.impuestos_item_venta * self.cantidad)
        super().save(*args, **kwargs)


class AlojamientoReserva(models.Model):
    id_alojamiento_reserva = models.AutoField(primary_key=True, verbose_name=_('ID Alojamiento'))
    venta = models.ForeignKey('Venta', related_name='alojamientos', on_delete=models.CASCADE, verbose_name=_('Venta'))
    item_venta = models.ForeignKey(ItemVenta, related_name='alojamientos_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
    nombre_establecimiento = models.CharField(_('Nombre Establecimiento'), max_length=150)
    check_in = models.DateField(_('Check In'), blank=True, null=True)
    check_out = models.DateField(_('Check Out'), blank=True, null=True)
    regimen_alimentacion = models.CharField(_('Régimen Alimentación'), max_length=30, blank=True, null=True, help_text=_('Ej: Desayuno, Media Pensión, Todo Incluido'))
    habitaciones = models.PositiveSmallIntegerField(_('Habitaciones'), default=1)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, verbose_name=_('Ciudad'))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Proveedor'))
    nombre_pasajero = models.CharField(_('Nombre Pasajero'), max_length=255, blank=True)
    localizador_proveedor = models.CharField(_('Localizador Proveedor'), max_length=100, blank=True)
    notas = models.TextField(_('Notas'), blank=True, null=True)

    class Meta:
        verbose_name = _('Alojamiento (Reserva)')
        verbose_name_plural = _('Alojamientos (Reservas)')
        ordering = ['check_in']

    def __str__(self):
        return f"{self.nombre_establecimiento} ({self.check_in or ''})"


class TrasladoServicio(models.Model):
    id_traslado_servicio = models.AutoField(primary_key=True, verbose_name=_('ID Traslado'))
    venta = models.ForeignKey('Venta', related_name='traslados', on_delete=models.CASCADE, verbose_name=_('Venta'))

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

    def __str__(self):
        return f"Traslado {self.origen or ''}->{self.destino or ''} {self.fecha_hora or ''}".strip()


class ActividadServicio(models.Model):
    id_actividad_servicio = models.AutoField(primary_key=True, verbose_name=_('ID Actividad'))
    venta = models.ForeignKey('Venta', related_name='actividades', on_delete=models.CASCADE, verbose_name=_('Venta'))
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

    def __str__(self):
        return self.nombre


class SegmentoVuelo(models.Model):
    id_segmento_vuelo = models.AutoField(primary_key=True, verbose_name=_('ID Segmento Vuelo'))
    venta = models.ForeignKey('Venta', related_name='segmentos_vuelo', on_delete=models.CASCADE, verbose_name=_('Venta'))
    origen = models.ForeignKey(Ciudad, related_name='segmentos_salida', on_delete=models.PROTECT, verbose_name=_('Ciudad Origen'))
    destino = models.ForeignKey(Ciudad, related_name='segmentos_llegada', on_delete=models.PROTECT, verbose_name=_('Ciudad Destino'))
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

    def __str__(self):
        return f"{self.origen} → {self.destino} {self.numero_vuelo or ''}".strip()


class FeeVenta(models.Model):
    id_fee_venta = models.AutoField(primary_key=True, verbose_name=_("ID Fee"))
    venta = models.ForeignKey(Venta, related_name='fees_venta', on_delete=models.CASCADE, verbose_name=_("Venta"))

    class TipoFee(models.TextChoices):
        EMISION = 'EMI', _('Emisión')
        CAMBIO = 'CAM', _('Cambio / Exchange')
        GESTION = 'GST', _('Gestión')
        URGENTE = 'URG', _('Urgente')
        OTRO = 'OTR', _('Otro')
    tipo_fee = models.CharField(_("Tipo Fee"), max_length=3, choices=TipoFee.choices, default=TipoFee.GESTION)
    descripcion = models.CharField(_("Descripción"), max_length=200, blank=True, null=True)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    es_comision_agencia = models.BooleanField(_("Es Comisión Agencia"), default=True)
    taxable = models.BooleanField(_("Sujeto a Impuestos"), default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Fee de Venta")
        verbose_name_plural = _("Fees de Venta")
        ordering = ['-creado']

    def __str__(self):
        return f"{self.get_tipo_fee_display()} {self.monto} {self.moneda.codigo_iso}"


class PagoVenta(models.Model):
    id_pago_venta = models.AutoField(primary_key=True, verbose_name=_("ID Pago"))
    venta = models.ForeignKey(Venta, related_name='pagos_venta', on_delete=models.CASCADE, verbose_name=_("Venta"))
    fecha_pago = models.DateTimeField(_("Fecha Pago"), default=timezone.now)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))

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
    notas = models.TextField(_("Notas"), blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Pago de Venta")
        verbose_name_plural = _("Pagos de Venta")
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Pago {self.monto} {self.moneda.codigo_iso} ({self.get_metodo_display()})"


class AlquilerAutoReserva(models.Model):
    id_alquiler_auto = models.AutoField(primary_key=True, verbose_name=_("ID Alquiler Auto"))
    venta = models.ForeignKey(Venta, related_name='alquileres_autos', on_delete=models.CASCADE, verbose_name=_("Venta"))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor"))
    ciudad_retiro = models.ForeignKey(Ciudad, related_name='autos_retiro', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad Retiro"))
    ciudad_devolucion = models.ForeignKey(Ciudad, related_name='autos_devolucion', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad Devolución"))
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


class EventoServicio(models.Model):
    id_evento_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Evento/Servicio"))
    venta = models.ForeignKey(Venta, related_name='eventos_servicios', on_delete=models.CASCADE, verbose_name=_("Venta"))
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


class CircuitoTuristico(models.Model):
    id_circuito = models.AutoField(primary_key=True, verbose_name=_("ID Circuito"))
    venta = models.ForeignKey(Venta, related_name='circuitos_turisticos', on_delete=models.CASCADE, verbose_name=_("Venta"))
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
            return self.precio_venta_estimado - self.costo_neto_estimado
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
    circuito = models.ForeignKey(CircuitoTuristico, related_name='dias', on_delete=models.CASCADE, verbose_name=_("Circuito"))
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


class PaqueteAereo(models.Model):
    id_paquete_aereo = models.AutoField(primary_key=True, verbose_name=_("ID Paquete Aéreo"))
    venta = models.ForeignKey(Venta, related_name='paquetes_aereos', on_delete=models.CASCADE, verbose_name=_("Venta"))
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
            return self.precio_venta_estimado - self.costo_neto_estimado
        return None

    @property
    def margen_pct(self):
        if self.margen_amount is not None and self.precio_venta_estimado not in (None, 0):
            try:
                return (self.margen_amount / self.precio_venta_estimado) * 100
            except Exception:
                return None
        return None


class ServicioAdicionalDetalle(models.Model):
    class TipoServicioChoices(models.TextChoices):
        SEGURO = 'SEG', _('Seguro')
        SIM = 'SIM', _('SIM / E-SIM')
        ASISTENCIA = 'AST', _('Asistencia')
        LOUNGE = 'LNG', _('Lounge')
        FASTTRACK = 'FST', _('Fast Track')
        OTRO = 'OTR', _('Otro')
    id_servicio_adicional = models.AutoField(primary_key=True, verbose_name=_("ID Servicio Adicional"))
    venta = models.ForeignKey(Venta, related_name='servicios_adicionales', on_delete=models.CASCADE, verbose_name=_("Venta"))
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
    venta = models.ForeignKey(Venta, related_name='metadata_parseo', on_delete=models.CASCADE, verbose_name=_("Venta"))
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

    def __str__(self):
        return f"Metadata Parseo Venta {self.venta_id} {self.fuente or ''} {self.creado:%Y-%m-%d %H:%M:%S}".strip()


class AuditLog(models.Model):
    class Accion(models.TextChoices):
        CREATE = 'CREATE', _('Creación')
        UPDATE = 'UPDATE', _('Actualización')
        DELETE = 'DELETE', _('Eliminación')
        STATE = 'STATE', _('Cambio de Estado')
    id_audit_log = models.AutoField(primary_key=True, verbose_name=_("ID Audit Log"))
    modelo = models.CharField(_("Modelo"), max_length=120, db_index=True)
    object_id = models.CharField(_("Object ID"), max_length=120, db_index=True)
    venta = models.ForeignKey('Venta', related_name='audit_logs', on_delete=models.CASCADE, blank=True, null=True, verbose_name=_("Venta Asociada"))
    accion = models.CharField(_("Acción"), max_length=10, choices=Accion.choices)
    descripcion = models.TextField(_("Descripción / Resumen"), blank=True, null=True)
    datos_previos = models.JSONField(_("Datos Previos"), blank=True, null=True)
    datos_nuevos = models.JSONField(_("Datos Nuevos"), blank=True, null=True)
    metadata_extra = models.JSONField(_("Metadata Extra"), blank=True, null=True)
    creado = models.DateTimeField(_("Creado"), auto_now_add=True, db_index=True)
    previous_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    record_hash = models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True)

    class Meta:
        verbose_name = _("Log de Auditoría")
        verbose_name_plural = _("Logs de Auditoría")
        ordering = ['-creado']

    def __str__(self):
        return f"AuditLog {self.modelo} {self.object_id} {self.accion} {self.creado:%Y-%m-%d %H:%M:%S}"  # pragma: no cover

    def save(self, *args, **kwargs):  # pragma: no cover
        import hashlib
        import json as _json

        from django.utils import timezone as _tz
        es_creacion = self.pk is None
        if es_creacion and not self.creado:
            self.creado = _tz.now()
        prev_hash = None
        if es_creacion and not self.previous_hash:
            ultimo = AuditLog.objects.order_by('-creado', '-id_audit_log').first()
            prev_hash = ultimo.record_hash if ultimo else None
            self.previous_hash = prev_hash
        super().save(*args, **kwargs)
        if es_creacion and not self.record_hash:
            payload = {'modelo': self.modelo, 'object_id': self.object_id, 'accion': self.accion, 'descripcion': self.descripcion or '', 'datos_previos': self.datos_previos, 'datos_nuevos': self.datos_nuevos, 'metadata_extra': self.metadata_extra, 'creado': self.creado.isoformat()}
            canon = _json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            base_str = (self.previous_hash or '') + '|' + canon
            self.record_hash = hashlib.sha256(base_str.encode('utf-8')).hexdigest()
            super().save(update_fields=['record_hash'])


def _crear_audit_log(*, modelo: str, object_id: str, accion: str, venta: Venta = None, descripcion: str = None, datos_previos=None, datos_nuevos=None, metadata_extra=None):  # pragma: no cover
    try:
        req_meta = get_current_request_meta()
        merged_meta = metadata_extra.copy() if metadata_extra else {}
        if req_meta:
            merged_meta.setdefault('ip', req_meta.get('ip'))
            merged_meta.setdefault('user_agent', req_meta.get('user_agent'))
        AuditLog.objects.create(modelo=modelo, object_id=str(object_id), accion=accion, venta=venta, descripcion=descripcion, datos_previos=datos_previos, datos_nuevos=datos_nuevos, metadata_extra=merged_meta or None)
    except Exception:
        logger.exception("Fallo creando AuditLog para %s %s", modelo, object_id)


@receiver(post_delete, sender=Venta)
def audit_delete_venta(sender, instance, **kwargs):  # pragma: no cover
    if sender is AuditLog:
        return
    _crear_audit_log(modelo='Venta', object_id=instance.pk, accion=AuditLog.Accion.DELETE, venta=None, descripcion=f"Venta eliminada {instance.pk}", metadata_extra={'venta_id': instance.pk})


@receiver(post_delete, sender=ItemVenta)
def audit_delete_itemventa(sender, instance, **kwargs):  # pragma: no cover
    if sender is AuditLog:
        return
    venta_rel = getattr(instance, 'venta', None)
    _crear_audit_log(modelo='ItemVenta', object_id=getattr(instance, 'pk', None), accion=AuditLog.Accion.DELETE, venta=venta_rel if isinstance(venta_rel, Venta) else None, descripcion=f"ItemVenta eliminado (venta {getattr(venta_rel, 'pk', 'N/A')})")


@receiver(post_save, sender=FeeVenta)
def recalc_venta_por_fee(sender, instance, created, **kwargs):  # pragma: no cover
    try:
        instance.venta.recalcular_finanzas()
    except Exception:
        pass

@receiver(post_save, sender=PagoVenta)
def recalc_venta_por_pago(sender, instance, created, **kwargs):  # pragma: no cover
    try:
        if instance.confirmado:
            instance.venta.recalcular_finanzas()
            instance.venta._evaluar_otorgar_puntos(contexto="signal_pago_post_save")
    except Exception:
        pass

@receiver(post_save, sender=Venta)
def enviar_email_confirmacion(sender, instance, created, **kwargs):
    """Envía email de confirmación cuando se crea una venta"""
    if created and instance.cliente and instance.cliente.email:
        try:
            from ..email_service import enviar_confirmacion_venta
            enviar_confirmacion_venta(instance)
        except Exception:
            logger.exception(f"Error enviando email confirmación para venta {instance.id_venta}")

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
    if not created and hasattr(instance, '_estado_anterior') and instance.cliente and instance.cliente.email:
        try:
            from ..email_service import enviar_cambio_estado
            enviar_cambio_estado(instance, instance._estado_anterior)
        except Exception:
            logger.exception(f"Error enviando email cambio estado para venta {instance.id_venta}")

__all__ = [
    'Venta','ItemVenta','AlojamientoReserva','TrasladoServicio','ActividadServicio','SegmentoVuelo',
    'FeeVenta','PagoVenta','AlquilerAutoReserva','EventoServicio','CircuitoTuristico','CircuitoDia',
    'PaqueteAereo','ServicioAdicionalDetalle','VentaParseMetadata','AuditLog'
]
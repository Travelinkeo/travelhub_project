from __future__ import annotations
import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from core.models.base import AgenciaMixin
from core.mixins import SoftDeleteModel
from apps.common.models import Ciudad
from .servicios import Proveedor

class AlojamientoReserva(SoftDeleteModel, AgenciaMixin, models.Model):
    id_alojamiento_reserva = models.AutoField(primary_key=True, verbose_name=_('ID Alojamiento'))
    venta = models.ForeignKey('bookings.Venta', related_name='alojamientos', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='alojamientos_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
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

class TrasladoServicio(SoftDeleteModel, AgenciaMixin, models.Model):
    id_traslado_servicio = models.AutoField(primary_key=True, verbose_name=_('ID Traslado'))
    venta = models.ForeignKey('bookings.Venta', related_name='traslados', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='traslados_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))

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

class ActividadServicio(SoftDeleteModel, AgenciaMixin, models.Model):
    id_actividad_servicio = models.AutoField(primary_key=True, verbose_name=_('ID Actividad'))
    venta = models.ForeignKey('bookings.Venta', related_name='actividades', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='actividades_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
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

class SegmentoVuelo(SoftDeleteModel, AgenciaMixin, models.Model):
    id_segmento_vuelo = models.AutoField(primary_key=True, verbose_name=_('ID Segmento Vuelo'))
    venta = models.ForeignKey('bookings.Venta', related_name='segmentos_vuelo', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='segmentos_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
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

class AlquilerAutoReserva(SoftDeleteModel, AgenciaMixin, models.Model):
    id_alquiler_auto = models.AutoField(primary_key=True, verbose_name=_("ID Alquiler Auto"))
    venta = models.ForeignKey('bookings.Venta', related_name='alquileres_autos', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='alquileres_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
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

class EventoServicio(SoftDeleteModel, AgenciaMixin, models.Model):
    id_evento_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Evento/Servicio"))
    venta = models.ForeignKey('bookings.Venta', related_name='eventos_servicios', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='eventos_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
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

class CircuitoTuristico(AgenciaMixin, models.Model):
    id_circuito = models.AutoField(primary_key=True, verbose_name=_("ID Circuito"))
    venta = models.ForeignKey('bookings.Venta', related_name='circuitos_turisticos', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='circuitos_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
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

    def save(self, *args, **kwargs):
        if self.fecha_inicio and self.dias_total and not self.fecha_fin:
            self.fecha_fin = self.fecha_inicio + datetime.timedelta(days=self.dias_total - 1)
        super().save(*args, **kwargs)

class CircuitoDia(AgenciaMixin, models.Model):
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

class PaqueteAereo(AgenciaMixin, models.Model):
    id_paquete_aereo = models.AutoField(primary_key=True, verbose_name=_("ID Paquete Aéreo"))
    venta = models.ForeignKey('bookings.Venta', related_name='paquetes_aereos', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='paquetes_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
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

class CruceroReserva(AgenciaMixin, models.Model):
    id_crucero = models.AutoField(primary_key=True, verbose_name=_("ID Crucero"))
    venta = models.ForeignKey('bookings.Venta', related_name='cruceros', on_delete=models.CASCADE, verbose_name=_('Venta'), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='cruceros_reserva', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
    nombre_crucero = models.CharField(_('Nombre del Crucero'), max_length=200)
    naviera = models.CharField(_('Naviera/Compañía'), max_length=150)
    nombre_barco = models.CharField(_('Nombre del Barco'), max_length=150, blank=True)
    fecha_embarque = models.DateField(_('Fecha de Embarque'))
    fecha_desembarque = models.DateField(_('Fecha de Desembarque'))
    noches = models.PositiveSmallIntegerField(_('Noches'))
    puerto_embarque = models.CharField(_('Puerto de Embarque'), max_length=150)
    puerto_desembarque = models.CharField(_('Puerto de Desembarque'), max_length=150)
    puertos_escala = models.JSONField(_('Puertos de Escala'), blank=True, null=True)
    dias_navegacion = models.PositiveSmallIntegerField(_('Días de Navegación'), default=0)

    class TipoCabina(models.TextChoices):
        INTERIOR = 'INT', _('Interior (sin ventana)')
        VENTANA = 'VEN', _('Vista al Mar (con ventana)')
        BALCON = 'BAL', _('Balcón Privado')
        SUITE = 'SUI', _('Suite')
        SUITE_PREMIUM = 'SUP', _('Suite Premium')
    
    tipo_cabina = models.CharField(_('Tipo de Cabina'), max_length=3, choices=TipoCabina.choices, default=TipoCabina.BALCON)
    numero_cabina = models.CharField(_('Número de Cabina'), max_length=20, blank=True)
    ubicacion_cabina = models.CharField(_('Ubicación en el Barco'), max_length=100, blank=True)
    clase_cabina = models.CharField(_('Clase de Cabina'), max_length=50, blank=True)
    numero_pasajeros = models.PositiveSmallIntegerField(_('Número de Pasajeros'), default=2)
    nombres_pasajeros = models.TextField(_('Nombres de Pasajeros'))
    paquete_bebidas = models.BooleanField(_('Paquete de Bebidas'), default=False)
    paquete_restaurantes = models.BooleanField(_('Paquete Restaurantes Especialidad'), default=False)
    paquete_spa = models.BooleanField(_('Paquete Spa y Bienestar'), default=False)
    paquete_wifi = models.BooleanField(_('Paquete Wi-Fi'), default=False)
    excursiones_tierra = models.JSONField(_('Excursiones en Tierra'), blank=True, null=True)
    pension_completa = models.BooleanField(_('Pensión Completa Incluida'), default=True)
    servicios_incluidos = models.TextField(_('Servicios Incluidos'), blank=True)
    servicios_no_incluidos = models.TextField(_('Servicios NO Incluidos'), blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Proveedor/Consolidador'))
    localizador_proveedor = models.CharField(_('Localizador Proveedor'), max_length=100, blank=True)
    tarifa_base_cabina = models.DecimalField(_('Tarifa Base Cabina'), max_digits=12, decimal_places=2, blank=True, null=True)
    es_comisionable = models.BooleanField(_('Es Comisionable'), default=True)
    porcentaje_comision = models.DecimalField(_('% Comisión'), max_digits=5, decimal_places=2, blank=True, null=True)
    monto_comision = models.DecimalField(_('Monto Comisión'), max_digits=12, decimal_places=2, blank=True, null=True, editable=False)
    fee_servicio_agencia = models.DecimalField(_('Fee Servicio Agencia'), max_digits=12, decimal_places=2, blank=True, null=True)
    costo_total_proveedor = models.DecimalField(_('Costo Total Proveedor'), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta_cliente = models.DecimalField(_('Precio Venta Cliente'), max_digits=12, decimal_places=2, blank=True, null=True)
    moneda = models.ForeignKey('finance.Moneda', on_delete=models.PROTECT, verbose_name=_('Moneda'), null=True, blank=True)
    observaciones = models.TextField(_('Observaciones'), blank=True)
    recomendaciones_cliente = models.TextField(_('Recomendaciones al Cliente'), blank=True)

    class Meta:
        verbose_name = _('Crucero')
        verbose_name_plural = _('Cruceros')
        ordering = ['fecha_embarque']
        db_table = 'core_cruceroreserva'

    def __str__(self):
        return f"{self.nombre_crucero} - {self.fecha_embarque}"

class ServicioAdicionalDetalle(AgenciaMixin, models.Model):
    class TipoServicioChoices(models.TextChoices):
        SEGURO = 'SEG', _('Seguro')
        SIM = 'SIM', _('SIM / E-SIM')
        ASISTENCIA = 'AST', _('Asistencia')
        LOUNGE = 'LNG', _('Lounge')
        FASTTRACK = 'FST', _('Fast Track')
        OTRO = 'OTR', _('Otro')
    id_servicio_adicional = models.AutoField(primary_key=True, verbose_name=_("ID Servicio Adicional"))
    venta = models.ForeignKey('bookings.Venta', related_name='servicios_adicionales', on_delete=models.CASCADE, verbose_name=_("Venta"), null=True, blank=True)
    item_venta = models.ForeignKey('bookings.ItemVenta', related_name='detalles_adicionales', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Item de Venta Asociado'))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor"))
    tipo_servicio = models.CharField(_("Tipo Servicio"), max_length=3, choices=TipoServicioChoices.choices, default=TipoServicioChoices.OTRO)
    descripcion = models.CharField(_("Descripción"), max_length=255, blank=True, null=True)
    codigo_referencia = models.CharField(_("Código Referencia"), max_length=100, blank=True, null=True)
    fecha_inicio = models.DateField(_("Fecha Inicio"), blank=True, null=True)
    fecha_fin = models.DateField(_("Fecha Fin"), blank=True, null=True)
    nombre_pasajero = models.CharField(_("Nombre Pasajero"), max_length=150, blank=True, null=True)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    costo_neto = models.DecimalField(_("Costo Neto"), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta = models.DecimalField(_("Precio Venta"), max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Servicio Adicional Detalle")
        verbose_name_plural = _("Servicios Adicionales Detalle")
        db_table = 'core_servicioadicionaldetalle'

    def __str__(self):
        return f"Servicio {self.tipo_servicio} {self.codigo_referencia or ''}".strip()

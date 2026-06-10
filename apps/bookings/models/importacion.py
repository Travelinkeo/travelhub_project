from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import (
    AgenciaMixin,
    RawFileStorage,
    SoftDeleteModel,
    antivirus_hook,
    validate_file_extension,
    validate_file_size,
)

logger = logging.getLogger(__name__)


class BoletoImportado(AgenciaMixin, SoftDeleteModel, models.Model):
    id_boleto_importado = models.AutoField(primary_key=True, verbose_name=_("ID Boleto Importado"))

    @property
    def id(self):
        """Alias para compatibilidad con interfaces genéricas del ORM y serializadores"""
        return self.id_boleto_importado

    @id.setter
    def id(self, value):
        self.id_boleto_importado = value

    archivo_boleto = models.FileField(
        _("Archivo del Boleto (.pdf, .txt, .eml)"),
        upload_to="boletos_importados/%Y/%m/",
        max_length=255,
        help_text=_("Suba el archivo del boleto en formato PDF, TXT o EML (máx 5MB)."),
        validators=[validate_file_size, validate_file_extension, antivirus_hook],
        blank=True,
        null=True,
        storage=RawFileStorage,
    )
    fecha_subida = models.DateTimeField(_("Fecha de Subida"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Fecha de Actualización"), auto_now=True)

    class FormatoDetectado(models.TextChoices):
        PDF_KIU = "PDF_KIU", _("PDF (KIU)")
        PDF_SABRE = "PDF_SAB", _("PDF (Sabre)")
        PDF_AMADEUS = "PDF_AMA", _("PDF (Amadeus)")
        TXT_KIU = "TXT_KIU", _("TXT (KIU)")
        TXT_SABRE = "TXT_SAB", _("TXT (Sabre)")
        TXT_AMADEUS = "TXT_AMA", _("TXT (Amadeus)")
        EML_KIU = "EML_KIU", _("EML (KIU)")
        EML_GENERAL = "EML_GEN", _("EML (General)")
        OTRO = "OTR", _("Otro/Desconocido")
        ERROR_FORMATO = "ERR", _("Error de Formato")

    formato_detectado = models.CharField(
        _("Formato Detectado"),
        max_length=20,
        choices=FormatoDetectado.choices,
        default=FormatoDetectado.OTRO,
        blank=True,
    )

    datos_parseados = models.JSONField(
        _("Datos Parseados"),
        blank=True,
        null=True,
        help_text=_("Información extraída del boleto en formato JSON."),
    )

    class EstadoParseo(models.TextChoices):
        PENDIENTE = "PEN", _("Pendiente de Parseo")
        EN_PROCESO = "PRO", _("En Proceso")
        COMPLETADO = "COM", _("Parseo Completado")
        REVISION_REQUERIDA = "REV", _("Revisión Requerida")
        ERROR_PARSEO = "ERR", _("Error en Parseo")
        NO_APLICA = "NAP", _("No Aplica Parseo")
        COLA_LLENA = "QUE", _("Pendiente (Cola Llena)")

    estado_parseo = models.CharField(
        _("Estado del Parseo"),
        max_length=3,
        choices=EstadoParseo.choices,
        default=EstadoParseo.PENDIENTE,
    )
    log_parseo = models.TextField(_("Log del Parseo"), blank=True, null=True)

    numero_boleto = models.CharField(_("Número de Boleto"), max_length=50, blank=True, null=True)
    nombre_pasajero_completo = models.CharField(
        _("Nombre Completo Pasajero (Original)"), max_length=150, blank=True, null=True
    )
    nombre_pasajero_procesado = models.CharField(
        _("Nombre Pasajero (Procesado)"), max_length=150, blank=True, null=True
    )
    ruta_vuelo = models.TextField(_("Ruta del Vuelo (Itinerario)"), blank=True, null=True)
    fecha_emision_boleto = models.DateField(_("Fecha de Emisión del Boleto"), blank=True, null=True)
    aerolinea_emisora = models.CharField(
        _("Aerolínea Emisora"), max_length=200, blank=True, null=True
    )
    direccion_aerolinea = models.TextField(_("Dirección Aerolínea"), blank=True, null=True)
    agente_emisor = models.CharField(_("Agente Emisor"), max_length=200, blank=True, null=True)
    foid_pasajero = models.CharField(
        _("FOID/D.Identidad Pasajero"), max_length=50, blank=True, null=True
    )
    localizador_pnr = models.CharField(_("Localizador (PNR)"), max_length=20, blank=True, null=True)
    tarifa_base = models.DecimalField(
        _("Tarifa Base"), max_digits=10, decimal_places=2, blank=True, null=True
    )
    impuestos_descripcion = models.TextField(_("Descripción Impuestos"), blank=True, null=True)
    impuestos_total_calculado = models.DecimalField(
        _("Total Impuestos (Calculado)"), max_digits=10, decimal_places=2, blank=True, null=True
    )
    total_boleto = models.DecimalField(
        _("Total del Boleto"), max_digits=10, decimal_places=2, blank=True, null=True
    )
    exchange_monto = models.DecimalField(
        _("Exchange"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Monto de exchange o diferencial de cambio asociado al boleto."),
    )
    void_monto = models.DecimalField(
        _("Void / Penalidad"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Monto asociado a VOID (penalidad / reembolso negativo)."),
    )
    comision_agencia = models.DecimalField(
        _("Comisión Agencia"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Comisión propia de la agencia respecto al boleto."),
    )

    iva_monto = models.DecimalField(
        _("Monto IVA"), max_digits=10, decimal_places=2, blank=True, null=True
    )
    inatur_monto = models.DecimalField(
        _("Monto Inatur (1%)"), max_digits=10, decimal_places=2, blank=True, null=True
    )
    otros_impuestos_monto = models.DecimalField(
        _("Otros Impuestos"), max_digits=10, decimal_places=2, blank=True, null=True
    )
    fee_servicio = models.DecimalField(
        _("Fee de Servicio"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Fee cobrado por la agencia por gestión del boleto."),
    )
    igtf_monto = models.DecimalField(
        _("IGTF"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_(
            "Impuesto a las Grandes Transacciones Financieras u otras retenciones locales."
        ),
    )

    proveedor_emisor = models.ForeignKey(
        "bookings.Proveedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Proveedor Emisor (Consolidador/Aerolínea)"),
    )

    venta_asociada = models.ForeignKey(
        "bookings.Venta",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="boletos_adjuntos",
        verbose_name=_("Venta/Reserva Asociada"),
    )

    archivo_pdf_generado = models.FileField(
        _("PDF Unificado Generado"),
        upload_to="boletos_generados/%Y/%m/",
        max_length=255,
        blank=True,
        null=True,
        help_text=_("El archivo PDF del boleto unificado, generado automáticamente."),
        storage=RawFileStorage,
    )

    telegram_file_id = models.CharField(
        _("Telegram File ID"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("ID del archivo en la nube de Telegram (para almacenamiento gratuito)."),
    )

    raw_hash = models.CharField(
        _("Hash del Contenido"),
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Hash SHA-256 para evitar duplicados."),
    )

    version = models.PositiveIntegerField(
        _("Versión"), default=1, help_text=_("Versión del boleto (1=Original, 2+=Re-emisión)")
    )

    boleto_padre = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versiones_posteriores",
        verbose_name=_("Boleto Padre (Versión Anterior)"),
    )

    class EstadoEmision(models.TextChoices):
        ORIGINAL = "ORI", _("Original")
        REEMISION = "REE", _("Re-emisión")
        ANULADO = "ANU", _("Anulado / Void")
        REEMBOLSO = "REM", _("Reembolso")

    estado_emision = models.CharField(
        _("Estado de Emisión"),
        max_length=3,
        choices=EstadoEmision.choices,
        default=EstadoEmision.ORIGINAL,
    )

    class Meta:
        verbose_name = _("Boleto Importado")
        verbose_name_plural = _("Boletos Importados")
        ordering = ["-fecha_subida"]
        indexes = [
            models.Index(fields=["agencia_id", "numero_boleto"]),
            models.Index(fields=["agencia_id", "localizador_pnr"]),
            models.Index(fields=["agencia_id", "fecha_subida"]),
            models.Index(fields=["agencia_id", "fecha_emision_boleto"]),
            models.Index(fields=["agencia_id", "aerolinea_emisora"]),
            models.Index(fields=["agencia_id", "localizador_pnr", "fecha_subida"]),
            models.Index(fields=["estado_parseo"], name="idx_boleto_estado_parseo"),
            models.Index(
                fields=["venta_asociada", "estado_emision"], name="idx_boleto_venta_estado"
            ),
            GinIndex(fields=["datos_parseados"], name="idx_boleto_json_gin"),
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_boleto_soft_delete_saas"),
        ]

    def __str__(self):
        return f"Boleto {self.id_boleto_importado} ({self.archivo_boleto.name if self.archivo_boleto else 'N/A'})"

    def get_pdf_url(self):
        """Devuelve la URL del PDF unificado si existe, sino None."""
        if self.archivo_pdf_generado:
            try:
                return self.archivo_pdf_generado.url
            except (ValueError, AttributeError):
                return None
        return None

    @property
    def pasajero_nombre_completo(self):
        return self.nombre_pasajero_completo

    @pasajero_nombre_completo.setter
    def pasajero_nombre_completo(self, value):
        self.nombre_pasajero_completo = value

    @property
    def pnr(self):
        return self.localizador_pnr

    @pnr.setter
    def pnr(self, value):
        self.localizador_pnr = value

    @property
    def id_boleto(self):
        return self.id_boleto_importado

    @id_boleto.setter
    def id_boleto(self, value):
        self.id_boleto_importado = value

    @property
    def fecha_emision(self):
        return self.fecha_emision_boleto

    @fecha_emision.setter
    def fecha_emision(self, value):
        self.fecha_emision_boleto = value


class SolicitudAnulacion(AgenciaMixin, models.Model):
    id_anulacion = models.AutoField(primary_key=True, verbose_name=_("ID Anulación"))
    boleto = models.ForeignKey(
        BoletoImportado,
        on_delete=models.CASCADE,
        related_name="solicitudes_anulacion",
        verbose_name=_("Boleto"),
        null=True,
        blank=True,
    )

    class TipoAnulacion(models.TextChoices):
        VOLUNTARIA = "VOL", _("Voluntaria")
        INVOLUNTARIA = "INV", _("Involuntaria")
        CAMBIO = "CAM", _("Cambio de Itinerario")
        OTRO = "OTR", _("Otro")

    tipo_anulacion = models.CharField(
        _("Tipo Anulación"),
        max_length=3,
        choices=TipoAnulacion.choices,
        default=TipoAnulacion.VOLUNTARIA,
    )

    motivo = models.TextField(_("Motivo"))
    monto_original = models.DecimalField(_("Monto Original"), max_digits=12, decimal_places=2)
    penalidad_aerolinea = models.DecimalField(
        _("Penalidad Aerolínea"), max_digits=12, decimal_places=2, default=0
    )
    fee_agencia = models.DecimalField(_("Fee Agencia"), max_digits=12, decimal_places=2, default=0)
    monto_reembolso = models.DecimalField(_("Monto a Reembolsar"), max_digits=12, decimal_places=2)

    class EstadoSolicitud(models.TextChoices):
        PENDIENTE = "PEN", _("Pendiente")
        APROBADA = "APR", _("Aprobada")
        RECHAZADA = "REC", _("Rechazada")
        PROCESADA = "PRO", _("Procesada")

    estado = models.CharField(
        _("Estado"),
        max_length=3,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.PENDIENTE,
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Solicitado Por"),
    )
    fecha_solicitud = models.DateTimeField(_("Fecha Solicitud"), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_("Fecha Actualización"), auto_now=True)

    class Meta:
        verbose_name = _("Solicitud de Anulación")
        verbose_name_plural = _("Solicitudes de Anulación")
        ordering = ["-fecha_solicitud"]

    def __str__(self):
        return f"Anulación {self.id_anulacion} - Boleto {self.id_anulacion}"


class BoletoImportadoTransito(AgenciaMixin, models.Model):
    id_transito = models.AutoField(primary_key=True, verbose_name=_("ID Tránsito"))
    boleto_origen = models.ForeignKey(
        BoletoImportado,
        on_delete=models.CASCADE,
        related_name="splits_transito",
        verbose_name=_("Boleto Origen"),
    )
    ticket_index = models.PositiveIntegerField(_("Índice de Ticket"), default=0)
    nombre_pasajero = models.CharField(_("Nombre Pasajero"), max_length=150, blank=True, null=True)
    numero_boleto = models.CharField(_("Número de Boleto"), max_length=50, blank=True, null=True)
    datos_json = models.JSONField(
        _("Datos Normalizados"), help_text=_("Datos de ticket normalizados staged en tránsito.")
    )
    procesado = models.BooleanField(_("Procesado"), default=False)
    fecha_creacion = models.DateTimeField(_("Fecha de Creación"), auto_now_add=True)

    class Meta:
        verbose_name = _("Boleto Importado en Tránsito")
        verbose_name_plural = _("Boletos Importados en Tránsito")
        ordering = ["id_transito"]
        indexes = [
            models.Index(fields=["agencia_id", "procesado"]),
            models.Index(fields=["boleto_origen_id", "procesado"]),
        ]

    def __str__(self):
        return f"Tránsito {self.id_transito} - Boleto {self.numero_boleto or 'N/A'} ({self.nombre_pasajero or 'N/A'})"

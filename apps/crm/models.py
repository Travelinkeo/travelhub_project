import logging
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin, EncryptedCharField, SoftDeleteModel

logger = logging.getLogger(__name__)


# ==========================================
# 1. MODELO CORE: CLIENTE
# ==========================================
class Cliente(AgenciaMixin, SoftDeleteModel, models.Model):
    id = models.AutoField(primary_key=True, db_column="id_cliente")

    @property
    def id_cliente(self):
        return self.id

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150, blank=True, null=True)
    nombre_empresa = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    telefono_principal = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    telefono_secundario = models.CharField(max_length=50, blank=True, null=True)

    direccion = models.TextField(blank=True, null=True)
    direccion_linea1 = models.CharField(max_length=255, blank=True, null=True)
    direccion_linea2 = models.CharField(max_length=255, blank=True, null=True)
    codigo_postal = models.CharField(max_length=20, blank=True, null=True)

    cedula_identidad = EncryptedCharField(max_length=255, blank=True, null=True)
    numero_pasaporte = EncryptedCharField(max_length=255, blank=True, null=True)
    documento_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)

    fecha_nacimiento = models.DateField(blank=True, null=True, db_index=True)
    fecha_expiracion_pasaporte = models.DateField(blank=True, null=True, db_index=True)
    fecha_registro = models.DateTimeField(default=timezone.now)

    ciudad = models.ForeignKey("common.Ciudad", on_delete=models.SET_NULL, null=True, blank=True)
    pais_emision_pasaporte = models.ForeignKey(
        "common.Pais",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_emision_pasaporte",
    )
    nacionalidad = models.ForeignKey(
        "common.Pais",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_nacionalidad",
    )

    class TipoCliente(models.TextChoices):
        PARTICULAR = "IND", "Individual / Particular"
        CORPORATIVO = "COR", "Corporativo / B2B"
        FREELANCE = "FRE", "Freelance / Aliado"
        MAYORISTA = "MAY", "Mayorista / Tour Operador"

    tipo_cliente = models.CharField(
        max_length=10, choices=TipoCliente.choices, default=TipoCliente.PARTICULAR
    )
    es_cliente_frecuente = models.BooleanField(default=False)
    puntos_fidelidad = models.PositiveIntegerField(default=0)
    preferencias_viaje = models.TextField(blank=True, null=True)
    notas_cliente = models.TextField(blank=True, null=True)
    foto_perfil = models.ImageField(upload_to="clientes/fotos/", blank=True, null=True)

    pasajeros = models.ManyToManyField("Pasajero", blank=True, related_name="clientes_asociados")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        indexes = [
            models.Index(fields=["agencia_id", "tipo_cliente"], name="idx_cliente_agencia_tipo"),
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_cliente_soft_delete_saas"),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos or ''}".strip()

    def calcular_cliente_frecuente(self):
        """
        Lógica para determinar si un cliente es frecuente.
        Por ahora, más de 1000 puntos o 5 ventas lo activan.
        """
        if self.puntos_fidelidad >= 1000:
            self.es_cliente_frecuente = True
        return self.es_cliente_frecuente

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos or ''}".strip()

    def get_nombre_completo(self):
        return self.nombre_completo


# ==========================================
# 2. MODELO KANBAN: OPORTUNIDAD (LEAD)
# ==========================================
class OportunidadViaje(AgenciaMixin, SoftDeleteModel, models.Model):
    class Etapa(models.TextChoices):
        NUEVO = "NEW", "Nuevo Lead"
        COTIZANDO = "QUO", "Armando Cotización"
        ESPERANDO_PAGO = "PAY", "Esperando Pago"
        GANADO = "WON", "Ganado (Vendido)"
        PERDIDO = "LOS", "Perdido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name="oportunidades", null=True, blank=True
    )

    origen = models.CharField(max_length=100, blank=True, null=True)
    destino = models.CharField(max_length=100, blank=True, null=True)
    fechas_texto = models.CharField(max_length=100, blank=True, null=True)
    cantidad_pasajeros = models.IntegerField(default=1)

    etapa = models.CharField(
        max_length=3, choices=Etapa.choices, default=Etapa.NUEVO, db_index=True
    )
    presupuesto_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    notas_ia = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Oportunidad de Viaje"
        verbose_name_plural = "Oportunidades de Viaje"
        indexes = [
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_lead_soft_delete_saas"),
        ]

    def __str__(self):
        return f"Lead: {self.destino} - {self.cliente.nombres}"


# ==========================================
# 3. MODELOS B2B2C: FREELANCERS Y COMISIONES
# ==========================================
class FreelancerProfile(AgenciaMixin, SoftDeleteModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_freelancer",
        null=True,
        blank=True,
    )
    # agencia la provee el Mixin automáticamente

    telefono = models.CharField(max_length=20, blank=True, null=True)
    comision_fija_por_boleto = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2, default=50.0)

    saldo_por_cobrar = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    total_historico_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Perfil de Freelancer"
        verbose_name_plural = "Perfiles de Freelancers"
        indexes = [
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_free_soft_delete_saas"),
        ]

    def __str__(self):
        return f"{self.usuario.get_full_name()} (Freelancer)"


class ComisionFreelancer(AgenciaMixin, SoftDeleteModel, models.Model):
    venta = models.OneToOneField(
        "bookings.Venta",
        on_delete=models.CASCADE,
        related_name="comision_asignada",
        null=True,
        blank=True,
    )
    freelancer = models.ForeignKey(
        FreelancerProfile,
        on_delete=models.CASCADE,
        related_name="comisiones_generadas",
        null=True,
        blank=True,
    )
    # agencia la provee el Mixin

    monto_base_venta = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    monto_comision_ganada = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    liquidada = models.BooleanField(default=False)
    fecha_liquidacion = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Comisión de Freelancer"
        verbose_name_plural = "Comisiones de Freelancers"
        indexes = [
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_freecom_soft_delete_saas"),
        ]

    def __str__(self):
        return f"Comisión {self.monto_comision_ganada} para {self.freelancer}"


# ==========================================
# 🛡️ MODELOS PERSISTENTES (Mantenidos para Estabilidad)
# ==========================================


class Pasajero(AgenciaMixin, SoftDeleteModel, models.Model):
    id_pasajero = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(blank=True, null=True)

    # agencia la provee el mixin

    numero_pasaporte = EncryptedCharField(max_length=255, blank=True, null=True)
    cedula_identidad = EncryptedCharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)

    nacionalidad = models.ForeignKey(
        "common.Pais",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pasajeros_nacionalidad",
    )
    pais_emision_documento = models.ForeignKey(
        "common.Pais", on_delete=models.SET_NULL, null=True, blank=True, db_column="pais_emision_id"
    )

    tipo_documento = models.CharField(max_length=4, default="PASS", db_index=True)
    fecha_emision_documento = models.DateField(blank=True, null=True)
    fecha_vencimiento_documento = models.DateField(
        blank=True, null=True, db_index=True, db_column="fecha_expiracion_documento"
    )
    fecha_vencimiento_pasaporte = models.DateField(blank=True, null=True, db_index=True)

    preferencias = models.JSONField(default=dict, blank=True)
    notas = models.TextField(blank=True, null=True)

    documento_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    tiene_fiebre_amarilla = models.BooleanField(default=False)
    fecha_vacuna_fiebre_amarilla = models.DateField(blank=True, null=True)
    foto_perfil = models.ImageField(upload_to="pasajeros/fotos/", blank=True, null=True)

    class Meta:
        verbose_name = "Pasajero"
        verbose_name_plural = "Pasajeros"
        indexes = [
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_pasajero_soft_delete_saas"),
            models.Index(
                fields=["agencia_id", "numero_pasaporte"], name="idx_pasajero_agencia_pasaporte"
            ),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def numero_documento(self):
        if self.numero_pasaporte:
            return self.numero_pasaporte
        if self.cedula_identidad:
            return self.cedula_identidad
        return ""

    def get_nombre_completo(self):
        return self.nombre_completo


class MensajeWhatsApp(AgenciaMixin, SoftDeleteModel, models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name="mensajes_whatsapp", null=True, blank=True
    )
    direccion = models.CharField(max_length=3, choices=[("IN", "Entrante"), ("OUT", "Saliente")])
    texto = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # agencia la provee el mixin

    class Meta:
        verbose_name = "Mensaje de WhatsApp"
        verbose_name_plural = "Mensajes de WhatsApp"
        indexes = [
            models.Index(fields=["is_deleted", "agencia_id"], name="idx_wa_soft_delete_saas"),
        ]

    def __str__(self):
        prefix = "WA OUT" if self.direccion == "OUT" else "WA IN"
        cliente_id = self.cliente_id if self.cliente_id else "?"
        return f"{prefix} #{self.pk} cli={cliente_id} {self.timestamp:%Y-%m-%d %H:%M}"


class PasaporteEscaneado(AgenciaMixin, models.Model):
    class ConfianzaChoices(models.TextChoices):
        HIGH = "HIGH", _("Alta")
        MEDIUM = "MEDIUM", _("Media")
        LOW = "LOW", _("Baja")

    class SexoChoices(models.TextChoices):
        M = "M", _("Masculino")
        F = "F", _("Femenino")

    imagen_original = models.ImageField(upload_to="pasaportes/%Y/%m/")
    imagen_procesada = models.ImageField(
        upload_to="pasaportes/processed/%Y/%m/", blank=True, null=True
    )
    numero_pasaporte = models.CharField(max_length=20, blank=True)
    nombres = models.CharField(max_length=100, blank=True)
    apellidos = models.CharField(max_length=100, blank=True)
    nacionalidad = models.CharField(max_length=3, blank=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=1, choices=SexoChoices.choices, blank=True)
    lugar_nacimiento = models.CharField(max_length=100, blank=True)
    confianza_ocr = models.CharField(
        max_length=10, choices=ConfianzaChoices.choices, default=ConfianzaChoices.MEDIUM
    )
    datos_ocr_completos = models.JSONField(default=dict)
    texto_mrz = models.TextField(blank=True)
    errores_detectados = models.JSONField(default=list)
    fecha_procesamiento = models.DateTimeField(auto_now_add=True)
    verificado_manualmente = models.BooleanField(default=False)

    cliente = models.ForeignKey("Cliente", on_delete=models.CASCADE, blank=True, null=True)
    procesado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True
    )

    class Meta:
        verbose_name = _("Pasaporte Escaneado")
        verbose_name_plural = _("Pasaportes Escaneados")
        ordering = ["-fecha_procesamiento"]

    def __str__(self):
        return f"Pasaporte {self.numero_pasaporte} - {self.nombres} {self.apellidos}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def es_valido(self):
        if not self.numero_pasaporte:
            return False
        from django.utils import timezone

        if self.fecha_vencimiento and self.fecha_vencimiento < timezone.now().date():
            return False
        return True

    def to_cliente_data(self):
        return {
            "nombres": self.nombres,
            "apellidos": self.apellidos,
            "nacionalidad": self.nacionalidad,
            "numero_pasaporte": self.numero_pasaporte,
            "fecha_nacimiento": self.fecha_nacimiento,
            "fecha_expiracion_pasaporte": self.fecha_vencimiento,
        }

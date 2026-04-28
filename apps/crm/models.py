import logging
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from core.mixins import SoftDeleteModel
from core.models.base import AgenciaMixin
from core.validators import validar_no_vacio_o_espacios
from core.fields import EncryptedCharField

logger = logging.getLogger(__name__)

# ==========================================
# 1. MODELO CORE: CLIENTE
# ==========================================
class Cliente(SoftDeleteModel, AgenciaMixin, models.Model):
    id = models.AutoField(primary_key=True, db_column='id_cliente')
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150, blank=True, null=True)
    nombre_empresa = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    telefono_principal = models.CharField(max_length=50, blank=True, null=True)
    telefono_secundario = models.CharField(max_length=50, blank=True, null=True)
    
    direccion = models.TextField(blank=True, null=True)
    direccion_linea1 = models.CharField(max_length=255, blank=True, null=True)
    direccion_linea2 = models.CharField(max_length=255, blank=True, null=True)
    codigo_postal = models.CharField(max_length=20, blank=True, null=True)
    
    cedula_identidad = EncryptedCharField(max_length=255, blank=True, null=True)
    numero_pasaporte = EncryptedCharField(max_length=255, blank=True, null=True)
    documento_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    
    fecha_nacimiento = models.DateField(blank=True, null=True)
    fecha_expiracion_pasaporte = models.DateField(blank=True, null=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    
    ciudad = models.ForeignKey('core.Ciudad', on_delete=models.SET_NULL, null=True, blank=True)
    pais_emision_pasaporte = models.ForeignKey('core.Pais', on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_emision_pasaporte')
    nacionalidad = models.ForeignKey('core.Pais', on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_nacionalidad')
    
    class TipoCliente(models.TextChoices):
        PARTICULAR = 'IND', 'Individual / Particular'
        CORPORATIVO = 'COR', 'Corporativo / B2B'
        FREELANCE = 'FRE', 'Freelance / Aliado'
        MAYORISTA = 'MAY', 'Mayorista / Tour Operador'
        
    tipo_cliente = models.CharField(max_length=10, choices=TipoCliente.choices, default=TipoCliente.PARTICULAR)
    es_cliente_frecuente = models.BooleanField(default=False)
    puntos_fidelidad = models.PositiveIntegerField(default=0)
    preferencias_viaje = models.TextField(blank=True, null=True)
    notas_cliente = models.TextField(blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='clientes/fotos/', blank=True, null=True)
    
    pasajeros = models.ManyToManyField('Pasajero', blank=True, related_name='clientes_asociados')

    class Meta:
        db_table = 'personas_cliente'
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.nombres} {self.apellidos or ''}".strip()

# ==========================================
# 2. MODELO KANBAN: OPORTUNIDAD (LEAD)
# ==========================================
class OportunidadViaje(AgenciaMixin, models.Model):
    class Etapa(models.TextChoices):
        NUEVO = 'NEW', 'Nuevo Lead'
        COTIZANDO = 'QUO', 'Armando Cotización'
        ESPERANDO_PAGO = 'PAY', 'Esperando Pago'
        GANADO = 'WON', 'Ganado (Vendido)'
        PERDIDO = 'LOS', 'Perdido'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='oportunidades', null=True, blank=True)
    
    origen = models.CharField(max_length=100, blank=True, null=True)
    destino = models.CharField(max_length=100, blank=True, null=True)
    fechas_texto = models.CharField(max_length=100, blank=True, null=True)
    cantidad_pasajeros = models.IntegerField(default=1)
    
    etapa = models.CharField(max_length=3, choices=Etapa.choices, default=Etapa.NUEVO)
    presupuesto_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    notas_ia = models.TextField(blank=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lead: {self.destino} - {self.cliente.nombres}"

# ==========================================
# 3. MODELOS B2B2C: FREELANCERS Y COMISIONES
# ==========================================
class FreelancerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_freelancer', null=True, blank=True)
    # FreelancerProfile ya tiene agencia, lo mantenemos igual por ahora o lo pasamos a Mixin si prefieres
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, related_name='freelancers_asociados', null=True, blank=True)
    
    telefono = models.CharField(max_length=20, blank=True, null=True)
    comision_fija_por_boleto = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2, default=50.0)
    
    saldo_por_cobrar = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    total_historico_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} (Freelancer)"

class ComisionFreelancer(models.Model):
    venta = models.OneToOneField('bookings.Venta', on_delete=models.CASCADE, related_name='comision_asignada', null=True, blank=True)
    freelancer = models.ForeignKey(FreelancerProfile, on_delete=models.CASCADE, related_name='comisiones_generadas', null=True, blank=True)
    
    monto_base_venta = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    monto_comision_ganada = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    liquidada = models.BooleanField(default=False)
    fecha_liquidacion = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comisión {self.monto_comision_ganada} para {self.freelancer}"

# ==========================================
# 🛡️ MODELOS PERSISTENTES (Mantenidos para Estabilidad)
# ==========================================

class Pasajero(SoftDeleteModel, AgenciaMixin, models.Model):
    id_pasajero = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    
    # agencia la provee el mixin
    
    numero_pasaporte = EncryptedCharField(max_length=255, blank=True, null=True)
    cedula_identidad = EncryptedCharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    
    nacionalidad = models.ForeignKey('core.Pais', on_delete=models.SET_NULL, null=True, blank=True, related_name='pasajeros_nacionalidad')
    pais_emision_documento = models.ForeignKey('core.Pais', on_delete=models.SET_NULL, null=True, blank=True, db_column='pais_emision_id')
    
    tipo_documento = models.CharField(max_length=4, default='PASS')
    fecha_emision_documento = models.DateField(blank=True, null=True)
    fecha_vencimiento_documento = models.DateField(blank=True, null=True, db_column='fecha_expiracion_documento')
    
    preferencias = models.JSONField(default=dict, blank=True)
    notas = models.TextField(blank=True, null=True)
    
    documento_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    tiene_fiebre_amarilla = models.BooleanField(default=False)
    fecha_vacuna_fiebre_amarilla = models.DateField(blank=True, null=True)
    
    class Meta:
        db_table = 'personas_pasajero'

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class MensajeWhatsApp(AgenciaMixin, models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='mensajes_whatsapp', null=True, blank=True)
    direccion = models.CharField(max_length=3, choices=[('IN', 'Entrante'), ('OUT', 'Saliente')])
    texto = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # agencia la provee el mixin

    class Meta:
        db_table = 'crm_whatsapp_mensaje'

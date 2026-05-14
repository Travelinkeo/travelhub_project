"""Modelo de Agencia para sistema multi-tenant."""

import logging

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from core.fields import EncryptedCharField

logger = logging.getLogger(__name__)


class Agencia(models.Model):
    """Perfil de la agencia de viajes (multi-tenant)."""
    
    # Información básica
    nombre = models.CharField(max_length=200, unique=True)
    nombre_comercial = models.CharField(max_length=200, blank=True)
    rif = models.CharField(max_length=20, blank=True, help_text="RIF o identificación fiscal")
    iata = models.CharField(max_length=20, blank=True, help_text="Código IATA")
    
    # Contacto
    telefono_principal = models.CharField(max_length=20, blank=True)
    telefono_secundario = models.CharField(max_length=20, blank=True)
    email_principal = models.EmailField()
    email_soporte = models.EmailField(blank=True)
    email_ventas = models.EmailField(blank=True)
    
    # Dirección
    direccion = models.TextField(blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, default="Venezuela")
    codigo_postal = models.CharField(max_length=10, blank=True)
    
    # --- COMPONENTES NORMALIZADOS (Fase 4) ---
    branding = models.OneToOneField('AgenciaBranding', on_delete=models.SET_NULL, null=True, blank=True, related_name='agencia_master')
    configuracion = models.OneToOneField('AgenciaConfiguracion', on_delete=models.SET_NULL, null=True, blank=True, related_name='agencia_master')
    
    # Redes sociales
    website = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=20, blank=True, help_text="Número con código de país")
    
    # Multi-tenant
    activa = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Propietario
    propietario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='agencias_propias', null=True, blank=True)
    
    class Meta:
        verbose_name = "Agencia"
        verbose_name_plural = "Agencias"
        ordering = ['nombre']
    
    # --- OPCIONES DE UI Y DOCUMENTOS (Fase 4) ---
    THEME_CHOICES = [
        ('obsidian', 'Obsidian Emerald'),
        ('swiss', 'Vintage Cream'),
        ('cyber', 'Cyber Fuchsia'),
        ('nordic', 'Nordic Snow'),
        ('midnight', 'Midnight Gold'),
        ('sunset', 'Sunset Rose'),
    ]
    
    PLANTILLAS_BOLETOS_CHOICES = [
        ('m1', 'Modelo Clásico'),
        ('m2', 'Editorial Plus'),
        ('m3', 'Executive Compact'),
        ('m4', 'Timeline Pro'),
        ('m5', 'Modern Digital'),
    ]

    PLANTILLAS_CHOICES = [
        ('m1', 'Modelo Estándar'),
        ('m2', 'Modelo Moderno'),
        ('m3', 'Modelo Minimalista'),
    ]

    def __str__(self):
        return f"{self.nombre} ({self.plan})"

    # --- CAPA DE COMPATIBILIDAD (READ-ONLY PROPERTIES) ---
    @property
    def plan(self):
        return self.configuracion.plan if self.configuracion else 'FREE'

    @property
    def logo(self):
        return self.branding.logo if self.branding else None

    @property
    def logo_pdf_base64(self):
        return self.branding.logo_pdf_base64 if self.branding else None

    @property
    def logo_dark(self):
        return self.branding.logo_dark if self.branding else None

    @property
    def logo_light(self):
        return self.branding.logo_light if self.branding else None

    @property
    def logo_telegram_url(self):
        return self.branding.logo_telegram_url if self.branding else None

    @property
    def logo_base64(self):
        return self.branding.logo_base64 if self.branding else None

    @property
    def logo_pdf_dark_base64(self):
        return self.branding.logo_pdf_dark_base64 if self.branding else None

    @property
    def subdominio_slug(self):
        return self.configuracion.subdominio_slug if self.configuracion else None

    @subdominio_slug.setter
    def subdominio_slug(self, value):
        if not self.configuracion:
            from core.models.agencia import AgenciaConfiguracion
            self.configuracion = AgenciaConfiguracion.objects.create()
        self.configuracion.subdominio_slug = value
        self.configuracion.save(update_fields=['subdominio_slug'])

    @property
    def moneda_principal(self):
        return self.configuracion.moneda_principal if self.configuracion else 'USD'

    @property
    def color_primario(self):
        return self.branding.color_primario if self.branding else '#1976d2'
    
    @property
    def email_monitor_active(self):
        return self.configuracion.email_monitor_active if self.configuracion else False

    @property
    def telegram_bot_token(self):
        return self.configuracion.telegram_bot_token if self.configuracion else None

    @property
    def telegram_chat_id(self):
        return self.configuracion.telegram_chat_id if self.configuracion else None

    @property
    def correo_emisiones(self):
        return self.configuracion.correo_emisiones if self.configuracion else None

    @property
    def password_app_correo(self):
        return self.configuracion.password_app_correo if self.configuracion else None


    @property
    def ui_theme(self):
        if self.branding:
            return self.branding.ui_theme
        return 'obsidian'

    @property
    def plantilla_boletos(self):
        if self.branding:
            return self.branding.plantilla_boletos
        return 'm1'

    @property
    def plantilla_vouchers(self):
        if self.branding:
            return self.branding.plantilla_vouchers
        return 'm1'

    @property
    def plantilla_facturas(self):
        if self.branding:
            return self.branding.plantilla_facturas
        return 'm1'

    @property
    def configuracion_api(self):
        return self.configuracion.configuracion_api if self.configuracion else {}

    @property
    def configuracion_correo(self):
        if not self.configuracion:
            return {}
        return {
            'EMAIL_HOST': self.configuracion.servidor_smtp,
            'EMAIL_PORT': self.configuracion.puerto_smtp,
            'EMAIL_HOST_USER': self.configuracion.correo_emisiones,
            'EMAIL_HOST_PASSWORD': self.configuracion.password_app_correo,
            'EMAIL_USE_TLS': self.configuracion.usar_tls,
            'DEFAULT_FROM_EMAIL': self.configuracion.correo_emisiones,
        }

    # --- MÉTODOS DE NEGOCIO ACTUALIZADOS ---
    def puede_crear_venta(self):
        """Verifica si puede crear más ventas este mes usando el servicio de cuotas."""
        from apps.common.services.saas_quota_service import SaaSQuotaService
        return SaaSQuotaService.check_quota(self, 'sales_per_month')
    
    def puede_agregar_usuario(self):
        """Verifica si puede agregar más usuarios usando el servicio de cuotas."""
        from apps.common.services.saas_quota_service import SaaSQuotaService
        return SaaSQuotaService.check_quota(self, 'users')
    
    def actualizar_limites_por_plan(self):
        """Actualiza límites según el plan configurado en settings.SAAS_PLAN_LIMITS."""
        if not self.configuracion: return
        
        limites = settings.SAAS_PLAN_LIMITS.get(self.configuracion.plan, settings.SAAS_PLAN_LIMITS['FREE'])
        
        self.configuracion.limite_usuarios = limites.get('users', 1)
        self.configuracion.limite_ventas_mes = limites.get('sales_per_month', 20)
        self.configuracion.save(update_fields=['limite_usuarios', 'limite_ventas_mes'])

    def save(self, *args, **kwargs):
        """
        Extensión de save para asegurar componentes SaaS y slug.
        """
        super().save(*args, **kwargs)

        # 1. Asegurar Componentes
        updated = False
        if not hasattr(self, 'configuracion') or not self.configuracion:
            self.configuracion = AgenciaConfiguracion.objects.create(agencia=self)
            updated = True
        if not hasattr(self, 'branding') or not self.branding:
            self.branding = AgenciaBranding.objects.create(agencia=self)
            updated = True
        
        if updated:
            # Volver a guardar para vincular los IDs de los componentes recién creados
            super().save(update_fields=['configuracion', 'branding'])

        # 2. Asegurar subdominio_slug en Configuración
        if self.configuracion and not self.configuracion.subdominio_slug:
            import uuid

            from django.utils.text import slugify
            base_slug = slugify(self.nombre)
            if not base_slug:
                base_slug = f"agencia-{uuid.uuid4().hex[:8]}"
            
            slug = base_slug
            counter = 1
            while AgenciaConfiguracion.objects.filter(subdominio_slug=slug).exclude(agencia=self).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.configuracion.subdominio_slug = slug
            self.configuracion.save(update_fields=['subdominio_slug'])
        
        # 3. Mantenimiento de logos (Legacy logic adaptada)
        try:
            from core.tasks import migrar_logos_agencia_task
            migrar_logos_agencia_task.delay(self.pk)
        except Exception as e:
            logger.error(f"❌ Error al disparar migrar_logos_agencia_task: {e}")


class UsuarioAgencia(models.Model):
    """Relación entre usuarios y agencias con roles."""
    
    ROLES = [
        ('admin', 'Administrador'),
        ('gerente', 'Gerente'),
        ('vendedor', 'Vendedor'),
        ('contador', 'Contador'),
        ('operador', 'Operador'),
        ('consulta', 'Solo Consulta'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agencias', null=True, blank=True)
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='usuarios', null=True, blank=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='vendedor')
    activo = models.BooleanField(default=True, db_index=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True, help_text="ID de chat de Telegram para notificaciones")
    
    class Meta:
        verbose_name = "Usuario de Agencia"
        verbose_name_plural = "Usuarios de Agencias"
        unique_together = ['usuario', 'agencia']
        ordering = ['agencia', 'usuario__username']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.agencia.nombre} ({self.get_rol_display()})"


class AgenciaBranding(models.Model):
    """Componente Estético de la Agencia (Branding & UI)."""
    agencia = models.OneToOneField(Agencia, on_delete=models.CASCADE, related_name='branding_v2')
    
    # Logos
    logo = models.ImageField(upload_to='agencias/logos/', blank=True, null=True)
    logo_light = models.ImageField(upload_to='agencias/logos/', blank=True, null=True)
    logo_dark = models.ImageField(upload_to='agencias/logos/', blank=True, null=True)
    logo_secundario = models.ImageField(upload_to='agencias/logos/', blank=True, null=True)
    
    logo_base64 = models.TextField(blank=True, null=True)
    logo_pdf_base64 = models.TextField(blank=True, null=True)
    logo_pdf_dark_base64 = models.TextField(blank=True, null=True)
    
    # Colores
    color_primario = models.CharField(max_length=7, default="#1976d2")
    color_secundario = models.CharField(max_length=7, default="#88081f")
    color_amadeus = models.CharField(max_length=7, default="#0c66e1")
    color_kiu = models.CharField(max_length=7, default="#0d1e40")
    color_copa = models.CharField(max_length=7, default="#0032a0")
    color_tk_connect = models.CharField(max_length=7, default="#232b38")
    color_wingo = models.CharField(max_length=7, default="#6633cb")
    color_travelport = models.CharField(max_length=7, default="#111827")
    
    # Telegram Storage fallback
    logo_telegram_id = models.CharField(max_length=150, blank=True, null=True)
    logo_telegram_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Textos
    eslogan = models.CharField(max_length=255, blank=True)
    pie_pagina = models.TextField(blank=True)
    terminos_condiciones = models.TextField(blank=True)
    
    # UI/Theme
    ui_theme = models.CharField(max_length=20, choices=Agencia.THEME_CHOICES, default='obsidian')
    plantilla_boletos = models.CharField(max_length=2, choices=Agencia.PLANTILLAS_BOLETOS_CHOICES, default='m1')
    plantilla_vouchers = models.CharField(max_length=2, choices=Agencia.PLANTILLAS_CHOICES, default='m1')
    plantilla_facturas = models.CharField(max_length=2, choices=Agencia.PLANTILLAS_CHOICES, default='m1')

    class Meta:
        verbose_name = "Agencia - Branding"
        verbose_name_plural = "Agencias - Branding"

    def __str__(self):
        return f"Branding: {self.agencia.nombre}"


class AgenciaConfiguracion(models.Model):
    """Componente Técnico y de Negocio (SaaS & API)."""
    agencia = models.OneToOneField(Agencia, on_delete=models.CASCADE, related_name='configuracion_v2')
    
    # Localización
    moneda_principal = models.CharField(max_length=3, default="USD")
    zona_horaria = models.CharField(max_length=50, default="America/Caracas")
    idioma = models.CharField(max_length=5, default="es")
    
    # SaaS Config (JSON)
    configuracion_correo = models.JSONField(default=dict, blank=True)
    configuracion_api = models.JSONField(default=dict, blank=True)
    configuracion_contable = models.JSONField(default=dict, blank=True)
    
    # Mailbot & Telegram
    correo_emisiones = models.EmailField(max_length=255, blank=True, null=True)
    password_app_correo = EncryptedCharField(max_length=255, blank=True, null=True)
    telegram_bot_token = EncryptedCharField(max_length=255, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Monitor IMAP
    email_monitor_user = models.EmailField(blank=True, null=True)
    email_monitor_password = EncryptedCharField(max_length=255, blank=True, null=True)
    email_monitor_active = models.BooleanField(default=False)
    email_monitor_last_check = models.DateTimeField(blank=True, null=True)
    
    # Fiscal (Venezuela)
    imprenta_digital_nombre = models.CharField(max_length=200, blank=True)
    imprenta_digital_rif = models.CharField(max_length=20, blank=True)
    imprenta_digital_providencia = models.CharField(max_length=50, blank=True)
    es_sujeto_pasivo_especial = models.BooleanField(default=False)
    esta_inscrita_rtn = models.BooleanField(default=False)
    
    # Plan & Límites
    plan = models.CharField(max_length=20, default='FREE')
    limite_mensual_boletos = models.PositiveIntegerField(default=100)
    limite_usuarios = models.IntegerField(default=1)
    limite_ventas_mes = models.IntegerField(default=50)
    ventas_mes_actual = models.IntegerField(default=0)
    
    # SaaS Status
    plan_status = models.CharField(max_length=20, default='active')
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    fecha_inicio_plan = models.DateField(default=timezone.now)
    fecha_fin_trial = models.DateField(null=True, blank=True)
    
    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    
    # Identidad SaaS
    subdominio_slug = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    es_demo = models.BooleanField(default=False)
    
    bi_insights = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Agencia - Configuración"
        verbose_name_plural = "Agencias - Configuraciones"

    def __str__(self):
        return f"Config: {self.agencia.nombre}"

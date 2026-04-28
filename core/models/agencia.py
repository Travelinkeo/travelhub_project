"""Modelo de Agencia para sistema multi-tenant."""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import logging

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
    
    # Branding
    logo = models.ImageField(upload_to='agencias/logos/', blank=True, null=True, help_text="Logo por defecto (fallback)")
    logo_light = models.ImageField(upload_to='agencias/logos/', blank=True, null=True, help_text="Logo para temas claros (Swiss, Nordic)")
    logo_dark = models.ImageField(upload_to='agencias/logos/', blank=True, null=True, help_text="Logo para temas oscuros (Obsidian, Cyber, etc.)")
    logo_secundario = models.ImageField(upload_to='agencias/logos/', blank=True, null=True, help_text="Logo alternativo para documentos")
    logo_base64 = models.TextField(blank=True, null=True, help_text="Logo codificado en Base64 (General)")
    logo_pdf_base64 = models.TextField(blank=True, null=True, help_text="Logo codificado en Base64 específico para inyección en reportes PDF (Modo Claro/Normal)")
    logo_pdf_dark_base64 = models.TextField(blank=True, null=True, help_text="Logo codificado en Base64 específico para inyección en reportes PDF (Modo Oscuro)")
    color_primario = models.CharField(max_length=7, default="#1976d2", help_text="Color hex (ej: #1976d2)")
    color_secundario = models.CharField(max_length=7, default="#88081f", help_text="Color hex Sabre")
    color_amadeus = models.CharField(max_length=7, default="#0c66e1", help_text="Color hex Amadeus")
    color_kiu = models.CharField(max_length=7, default="#0d1e40", help_text="Color hex KIU")
    color_copa = models.CharField(max_length=7, default="#0032a0", help_text="Color hex Copa (SPRK)")
    color_tk_connect = models.CharField(max_length=7, default="#232b38", help_text="Color hex TK Connect")
    color_wingo = models.CharField(max_length=7, default="#6633cb", help_text="Color hex Wingo")
    color_travelport = models.CharField(max_length=7, default="#111827", help_text="Color hex Travelport")
    
    # Storage Externo (Telegram API Phase 26)
    logo_telegram_id = models.CharField(max_length=150, blank=True, null=True, help_text="ID del archivo en Telegram Storage")
    logo_telegram_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL proxy/cache del logo en Telegram")

    # Redes sociales
    website = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=20, blank=True, help_text="Número con código de país")
    
    # Configuración
    moneda_principal = models.CharField(max_length=3, default="USD", help_text="Código ISO de moneda")
    zona_horaria = models.CharField(max_length=50, default="America/Caracas")
    idioma = models.CharField(max_length=5, default="es", help_text="Código ISO de idioma")
    
    # Textos Legales y Branding
    eslogan = models.CharField(max_length=255, blank=True, help_text="Eslogan comercial (Ej: Viajar es Vivir)")
    pie_pagina = models.TextField(blank=True, help_text="Texto legal o de contacto al pie de los documentos PDF")
    terminos_condiciones = models.TextField(blank=True, help_text="Términos y condiciones generales para vouchers y facturas")

    
    # Theme Engine
    THEME_CHOICES = [
        ('obsidian', 'Obsidian Emerald (Oscuro)'),
        ('swiss', 'Swiss Vintage (Claro)'),
        ('cyber', 'Cyber Fuchsia (Oscuro)'),
        ('nordic', 'Nordic Snow (Claro)'),
        ('midnight', 'Midnight Gold (Oscuro)'),
        ('sunset', 'Neon Sunset (Oscuro)'),
    ]
    ui_theme = models.CharField(
        max_length=20, 
        choices=THEME_CHOICES, 
        default='obsidian', 
        help_text="Tema visual de la interfaz de usuario."
    )

    # --- OPCIONES DE PLANTILLAS ---
    PLANTILLAS_BOLETOS_CHOICES = [
        ('m1', 'Golden Premium (Legacy)'),
        ('m2', 'Editorial Plus (Luxury)'),
        ('m3', 'Executive Compact (Dense)'),
        ('m4', 'Timeline Pro (Visual)'),
        ('m5', 'Modern Tech (Minimal)'),
    ]
    PLANTILLAS_VOUCHERS_CHOICES = [
        ('m1', 'Classic Corporate (Base)'),
        ('m2', 'Editorial Plus (Editorial)'),
        ('m3', 'Executive Compact (Dense)'),
        ('m4', 'Timeline Experience (Visual)'),
        ('m5', 'Modern Digital (Minimal)'),
    ]
    
    plantilla_boletos = models.CharField(
        max_length=2,
        choices=PLANTILLAS_BOLETOS_CHOICES,
        default='m1',
        help_text="Diseño estructural para Boletos (TKT)"
    )
    plantilla_vouchers = models.CharField(
        max_length=2,
        choices=PLANTILLAS_VOUCHERS_CHOICES,
        default='m1',
        help_text="Diseño estructural para Vouchers Multiservicio"
    )
    plantilla_facturas = models.CharField(
        max_length=2,
        choices=PLANTILLAS_VOUCHERS_CHOICES,
        default='m1',
        help_text="Diseño estructural para Facturas Fiscales"
    )
    
    # Configuración SaaS (Multi-tenant)
    configuracion_correo = models.JSONField(default=dict, blank=True, help_text="Configuración SMTP: EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD")
    
    # --- CONFIGURACIÓN SAAS: MAILBOT Y TELEGRAM ---
    correo_emisiones = models.EmailField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Correo exclusivo donde esta agencia recibe los boletos del GDS"
    )
    password_app_correo = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Contraseña de Aplicación (Ej. Google App Password) para lectura IMAP"
    )
    telegram_bot_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Token del Bot de Telegram exclusivo de esta agencia (Opcional)"
    )
    telegram_chat_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="ID del Chat/Grupo de Telegram donde llegarán los Vouchers de esta agencia"
    )

    # Mailbot Monitor (SaaS)
    email_monitor_user = models.EmailField(blank=True, null=True, help_text="Email a monitorear para boletos (Gmail)")
    email_monitor_password = models.CharField(max_length=255, blank=True, null=True, help_text="Contraseña de Aplicación de Google (o Token)")
    email_monitor_active = models.BooleanField(default=False, help_text="Activar monitoreo automático")
    email_monitor_last_check = models.DateTimeField(blank=True, null=True, help_text="Último chequeo realizado")
    
    configuracion_api = models.JSONField(default=dict, blank=True, help_text="Claves de API: WHATSAPP_TOKEN, BCV_TOKEN, etc.")
    
    # Facturación Venezuela - Imprenta Digital
    imprenta_digital_nombre = models.CharField(max_length=200, blank=True, help_text="Razón Social de la Imprenta Digital Autorizada")
    imprenta_digital_rif = models.CharField(max_length=20, blank=True, help_text="RIF de la Imprenta Digital")
    imprenta_digital_providencia = models.CharField(max_length=50, blank=True, help_text="Número de Providencia SENIAT (ej: SNAT/2024/XXXXX)")
    es_sujeto_pasivo_especial = models.BooleanField(default=False, help_text="Contribuyente Especial SENIAT")
    esta_inscrita_rtn = models.BooleanField(default=False, help_text="Inscrita en Registro Turístico Nacional")
    
    # Plan SaaS y Límites
    PLAN_CHOICES = [
        ('FREE', 'Gratuito (Trial 30 días)'),
        ('BASIC', 'Básico - $29/mes'),
        ('PRO', 'Profesional - $99/mes'),
        ('ENTERPRISE', 'Enterprise - $299/mes'),
    ]
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE')
    limite_mensual_boletos = models.PositiveIntegerField(default=100)
    bi_insights = models.JSONField(default=dict, blank=True, help_text="Consejos y análisis de IA para el Dashboard del CEO.")
    fecha_inicio_plan = models.DateField(default=timezone.now)
    fecha_fin_trial = models.DateField(null=True, blank=True)
    
    # Límites por plan
    limite_usuarios = models.IntegerField(default=1)
    limite_ventas_mes = models.IntegerField(default=50)
    ventas_mes_actual = models.IntegerField(default=0)
    
    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    
    # SaaS Identity
    subdominio_slug = models.CharField(
        max_length=100, 
        unique=True, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="Slug para la URL personalizada (ej: miagencia.travelhub.cc)"
    )
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('past_due', 'Pago Pendiente'),
        ('canceled', 'Cancelado'),
        ('incomplete', 'Incompleto'),
    ]
    plan_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    # Flags especiales
    es_demo = models.BooleanField(default=False, help_text="Agencia de demostración")
    
    # Multi-tenant
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Propietario
    propietario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='agencias_propias', null=True, blank=True)
    
    class Meta:
        verbose_name = "Agencia"
        verbose_name_plural = "Agencias"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_plan_display()})"
    
    def puede_crear_venta(self):
        """Verifica si puede crear más ventas este mes."""
        if self.plan == 'ENTERPRISE':
            return True
        return self.ventas_mes_actual < self.limite_ventas_mes
    
    def puede_agregar_usuario(self):
        """Verifica si puede agregar más usuarios."""
        if self.plan == 'ENTERPRISE':
            return True
        return self.usuarios.filter(activo=True).count() < self.limite_usuarios
    
    def actualizar_limites_por_plan(self):
        """Actualiza límites según el plan."""
        limites = {
            'FREE': {'usuarios': 1, 'ventas': 50},
            'BASIC': {'usuarios': 3, 'ventas': 200},
            'PRO': {'usuarios': 10, 'ventas': 1000},
            'ENTERPRISE': {'usuarios': 999999, 'ventas': 999999},
        }
        limite = limites.get(self.plan, limites['FREE'])
        self.limite_usuarios = limite['usuarios']
        self.limite_ventas_mes = limite['ventas']
        self.save(update_fields=['limite_usuarios', 'limite_ventas_mes'])

    def save(self, *args, **kwargs):
        """
        Extensión de save para mover logos a Telegram Storage (Phase 26).
        Se ejecuta de forma asíncrona para evitar bloqueos HTTP.
        """
        # Guardar primero para asegurar que tenemos ID y datos persistidos
        super().save(*args, **kwargs)
        
        # Disparar tarea asíncrona (Solo si no viene de un update_fields de la misma tarea)
        if kwargs.get('update_fields') and 'logo_telegram_id' in kwargs.get('update_fields'):
            return
            
        try:
            from core.tasks import migrar_logos_agencia_task
            migrar_logos_agencia_task.delay(self.pk)
        except Exception as e:
            logger.error(f"❌ Error al disparar migrar_logos_agencia_task para agencia {self.pk}: {e}")
            # No relanzamos la excepción para evitar romper el flujo de guardado en la UI




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
    activo = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True, help_text="ID de chat de Telegram para notificaciones")
    
    class Meta:
        verbose_name = "Usuario de Agencia"
        verbose_name_plural = "Usuarios de Agencias"
        unique_together = ['usuario', 'agencia']
        ordering = ['agencia', 'usuario__username']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.agencia.nombre} ({self.get_rol_display()})"

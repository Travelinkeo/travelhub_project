"""Modelo de Agencia para sistema multi-tenant."""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
    logo = models.ImageField(upload_to='agencias/logos/', blank=True, null=True)
    logo_secundario = models.ImageField(upload_to='agencias/logos/', blank=True, null=True, help_text="Logo alternativo para documentos")
    color_primario = models.CharField(max_length=7, default="#1976d2", help_text="Color hex (ej: #1976d2)")
    color_secundario = models.CharField(max_length=7, default="#dc004e", help_text="Color hex (ej: #dc004e)")
    
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
        ('ENTERPRISE', 'Enterprise - Personalizado'),
    ]
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE')
    fecha_inicio_plan = models.DateField(default=timezone.now)
    fecha_fin_trial = models.DateField(null=True, blank=True)
    
    # Límites por plan
    limite_usuarios = models.IntegerField(default=1)
    limite_ventas_mes = models.IntegerField(default=50)
    ventas_mes_actual = models.IntegerField(default=0)
    
    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    
    # Flags especiales
    es_demo = models.BooleanField(default=False, help_text="Agencia de demostración")
    
    # Multi-tenant
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Propietario
    propietario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='agencias_propias')
    
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
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agencias')
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='usuarios')
    rol = models.CharField(max_length=20, choices=ROLES, default='vendedor')
    activo = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Usuario de Agencia"
        verbose_name_plural = "Usuarios de Agencias"
        unique_together = ['usuario', 'agencia']
        ordering = ['agencia', 'usuario__username']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.agencia.nombre} ({self.get_rol_display()})"

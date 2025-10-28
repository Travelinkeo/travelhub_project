from django.db import models
from django.core.validators import RegexValidator
from personas.models import Cliente

class PasaporteEscaneado(models.Model):
    """Modelo para almacenar datos de pasaportes escaneados"""
    
    CONFIANZA_CHOICES = [
        ('HIGH', 'Alta'),
        ('MEDIUM', 'Media'),
        ('LOW', 'Baja'),
    ]
    
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]
    
    # Relaciones
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    
    # Imagen
    imagen_original = models.ImageField(upload_to='pasaportes/%Y/%m/')
    imagen_procesada = models.ImageField(upload_to='pasaportes/processed/%Y/%m/', null=True, blank=True)
    
    # Datos extraídos
    numero_pasaporte = models.CharField(max_length=20, blank=True)
    nombres = models.CharField(max_length=100, blank=True)
    apellidos = models.CharField(max_length=100, blank=True)
    nacionalidad = models.CharField(max_length=3, blank=True)  # Código ISO 3 letras
    fecha_nacimiento = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True)
    lugar_nacimiento = models.CharField(max_length=100, blank=True)
    
    # Metadatos del procesamiento
    confianza_ocr = models.CharField(max_length=10, choices=CONFIANZA_CHOICES, default='MEDIUM')
    datos_ocr_completos = models.JSONField(default=dict)  # Todos los datos extraídos
    texto_mrz = models.TextField(blank=True)  # Zona legible por máquina
    errores_detectados = models.JSONField(default=list)  # Lista de errores/advertencias
    
    # Auditoría
    fecha_procesamiento = models.DateTimeField(auto_now_add=True)
    procesado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    verificado_manualmente = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'core_pasaporte_escaneado'
        verbose_name = 'Pasaporte Escaneado'
        verbose_name_plural = 'Pasaportes Escaneados'
        ordering = ['-fecha_procesamiento']
    
    def __str__(self):
        if self.numero_pasaporte:
            return f"Pasaporte {self.numero_pasaporte} - {self.nombres} {self.apellidos}"
        return f"Pasaporte #{self.id} - {self.fecha_procesamiento.strftime('%d/%m/%Y')}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()
    
    @property
    def es_valido(self):
        """Verifica si el pasaporte tiene datos mínimos válidos"""
        return bool(
            self.numero_pasaporte and 
            self.nombres and 
            self.apellidos and
            self.fecha_vencimiento
        )
    
    def to_cliente_data(self):
        """Convierte datos del pasaporte a formato para crear/actualizar cliente"""
        from core.models_catalogos import Pais
        
        data = {
            'nombres': self.nombres or 'Sin nombre',
            'apellidos': self.apellidos or 'Sin apellido',
            'numero_pasaporte': self.numero_pasaporte,
            'fecha_nacimiento': self.fecha_nacimiento,
            'fecha_expiracion_pasaporte': self.fecha_vencimiento,
        }
        
        # Convertir código ISO de nacionalidad a instancia de País
        if self.nacionalidad:
            try:
                pais = Pais.objects.filter(codigo_iso_3=self.nacionalidad).first()
                if pais:
                    data['nacionalidad'] = pais  # Asignar instancia, no ID
                    data['pais_emision_pasaporte'] = pais  # Asignar instancia, no ID
            except Exception:
                pass
        
        return data
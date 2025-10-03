from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models.pasaportes import PasaporteEscaneado
from .services.passport_ocr_service import PassportOCRService

@receiver(post_save, sender=PasaporteEscaneado)
def process_passport_on_save(sender, instance, created, **kwargs):
    """Procesa automáticamente el pasaporte cuando se guarda"""
    if created and instance.imagen_original and not instance.numero_pasaporte:
        try:
            ocr_service = PassportOCRService()
            result = ocr_service.process_passport_image(instance.imagen_original)
            
            if result['success']:
                data = result['data']
                # Convertir fechas a string para JSON
                json_safe_data = {}
                for key, value in data.items():
                    if hasattr(value, 'strftime'):  # Es una fecha
                        json_safe_data[key] = value.strftime('%Y-%m-%d')
                    else:
                        json_safe_data[key] = value
                
                # Actualizar campos sin crear loop infinito
                instance.numero_pasaporte = data.get('numero_pasaporte', '')
                instance.nombres = data.get('nombres', '')
                instance.apellidos = data.get('apellidos', '')
                instance.nacionalidad = data.get('nacionalidad', '')
                instance.fecha_nacimiento = data.get('fecha_nacimiento')
                instance.fecha_vencimiento = data.get('fecha_vencimiento')
                instance.sexo = data.get('sexo', '')
                instance.confianza_ocr = result['confidence']
                instance.datos_ocr_completos = json_safe_data
                instance.texto_mrz = data.get('texto_mrz', '')
                instance.save(update_fields=[
                    'numero_pasaporte', 'nombres', 'apellidos', 'nacionalidad',
                    'fecha_nacimiento', 'fecha_vencimiento', 'sexo', 'confianza_ocr',
                    'datos_ocr_completos', 'texto_mrz'
                ])
        except Exception as e:
            # Log error but don't fail the save
            print(f"Error procesando pasaporte: {e}")
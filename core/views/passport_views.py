from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from core.services.passport_ocr_service import PassportOCRService
from core.models.pasaportes import PasaporteEscaneado
from personas.models import Cliente
import json

@api_view(['POST'])
def upload_passport(request):
    """Sube y procesa imagen de pasaporte"""
    
    if 'passport_image' not in request.FILES:
        return Response({
            'error': 'No se proporcionó imagen de pasaporte'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    image_file = request.FILES['passport_image']
    
    # Validar tipo de archivo
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
    if image_file.content_type not in allowed_types:
        return Response({
            'error': 'Tipo de archivo no válido. Use JPG o PNG'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Procesar imagen con OCR
        ocr_service = PassportOCRService()
        result = ocr_service.process_passport_image(image_file)
        
        if not result['success']:
            return Response({
                'error': f'Error procesando imagen: {result.get("error", "Error desconocido")}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear registro en base de datos
        passport_data = result['data']
        pasaporte = PasaporteEscaneado.objects.create(
            imagen_original=image_file,
            numero_pasaporte=passport_data.get('numero_pasaporte', ''),
            nombres=passport_data.get('nombres', ''),
            apellidos=passport_data.get('apellidos', ''),
            nacionalidad=passport_data.get('nacionalidad', ''),
            sexo=passport_data.get('sexo', ''),
            confianza_ocr=result['confidence'],
            texto_mrz=passport_data.get('texto_mrz', ''),
        )
        
        return Response({
            'success': True,
            'passport_id': pasaporte.id,
            'data': {
                'numero_pasaporte': pasaporte.numero_pasaporte or '',
                'nombres': pasaporte.nombres or '',
                'apellidos': pasaporte.apellidos or '',
                'nacionalidad': pasaporte.nacionalidad or '',
                'fecha_nacimiento': '',
                'fecha_vencimiento': '',
                'sexo': pasaporte.sexo or '',
                'confianza': pasaporte.confianza_ocr or 'LOW',
                'es_valido': bool(pasaporte.numero_pasaporte)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_client_from_passport(request, passport_id):
    """Crea cliente desde datos de pasaporte escaneado"""
    
    try:
        pasaporte = PasaporteEscaneado.objects.get(id=passport_id)
        
        if not pasaporte.numero_pasaporte:
            return Response({
                'error': 'Pasaporte debe tener al menos el número para crear cliente'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar si ya existe cliente con este pasaporte
        existing_client = Cliente.objects.filter(
            numero_pasaporte=pasaporte.numero_pasaporte
        ).first()
        
        if existing_client:
            # Actualizar cliente existente
            client_data = pasaporte.to_cliente_data()
            for key, value in client_data.items():
                if value:  # Solo actualizar campos no vacíos
                    setattr(existing_client, key, value)
            existing_client.save()
            
            # Asociar pasaporte al cliente
            pasaporte.cliente = existing_client
            pasaporte.save()
            
            return Response({
                'success': True,
                'action': 'updated',
                'client_id': existing_client.id_cliente,
                'message': 'Cliente actualizado con datos del pasaporte'
            })
        else:
            # Crear nuevo cliente
            client_data = pasaporte.to_cliente_data()
            nuevo_cliente = Cliente.objects.create(**client_data)
            
            # Asociar pasaporte al cliente
            pasaporte.cliente = nuevo_cliente
            pasaporte.save()
            
            return Response({
                'success': True,
                'action': 'created',
                'client_id': nuevo_cliente.id_cliente,
                'message': 'Cliente creado desde datos del pasaporte'
            })
            
    except PasaporteEscaneado.DoesNotExist:
        return Response({
            'error': 'Pasaporte no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error creando cliente: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
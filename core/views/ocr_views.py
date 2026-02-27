from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render
from core.services.passport_ocr_service import PassportOCRService
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class OCRPassportView(View):
    """
    API endpoint para procesar imágenes de pasaporte.
    POST /api/ocr/passport/
    """
    def post(self, request, *args, **kwargs):
        if 'archivo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No se proporcionó ningún archivo de imagen.'}, status=400)
        
        archivo = request.FILES['archivo']
        
        try:
            service = PassportOCRService()
            result = service.process_passport_image(archivo)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'data': result['data'],
                    'message': 'Pasaporte procesado exitosamente'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Error desconocido al procesar')
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error interno OCR: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

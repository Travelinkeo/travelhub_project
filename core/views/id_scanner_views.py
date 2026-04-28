import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from core.services.id_scanner_service import IDScannerService
from apps.crm.models import Pasajero

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class CedulaScannerAPIView(View):
    """
    API para escanear cédulas, extraer datos y recortar rostros.
    POST /api/crm/cedula-scanner/
    """
    def post(self, request, *args, **kwargs):
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No se recibió ninguna imagen'}, status=400)

        image_file = request.FILES['image']
        
        # Obtener agencia de forma robusta
        agencia = getattr(request.user, 'agencia', None)
        if not agencia:
            from core.middleware import get_current_agency
            agencia = get_current_agency()

        # 1. Llamar al servicio de escaneo e IA
        resultado = IDScannerService.procesar_cedula(image_file, agencia=agencia)
        
        if "error" in resultado:
            return JsonResponse({'error': resultado['error']}, status=500)

        # 2. Lógica de Negocio: Upsert del Pasajero
        cedula_num = resultado.get('cedula')
        foto_recortada = resultado.pop('foto_recortada', None)
        
        # Sanitizar campos: si la IA no extrajo datos, dejamos VACÍO (nunca un placeholder)
        final_nombres = (str(resultado.get('nombres') or '').strip())[:50]
        final_apellidos = (str(resultado.get('apellidos') or '').strip())[:50]
        final_cedula_str = (str(cedula_num or '').strip())[:15]

        try:
            with transaction.atomic():
                # Buscar por cédula limpia (intento con el integer limpio)
                # Convertir cédula a int de forma segura
                cedula_int = int(cedula_num) if cedula_num and str(cedula_num).isdigit() else 0
                pasajero, created = Pasajero.objects.get_or_create(
                    cedula_limpia=cedula_int,
                    agencia=agencia,
                    defaults={
                        'nombres': final_nombres,
                        'apellidos': final_apellidos,
                        'cedula_identidad': final_cedula_str,
                        'nombres_ocr': final_nombres,
                        'apellidos_ocr': final_apellidos,
                        'fecha_nacimiento_ocr': resultado.get('fecha_nacimiento'),
                        'tipo_documento': 'CI'
                    }
                )

                if not created:
                    # Actualizar si ya existe
                    pasajero.nombres_ocr = final_nombres
                    pasajero.apellidos_ocr = final_apellidos
                    pasajero.fecha_nacimiento_ocr = resultado.get('fecha_nacimiento')
                    # Actualizamos campos principales si están vacíos
                    if not pasajero.fecha_nacimiento:
                        pasajero.fecha_nacimiento = resultado.get('fecha_nacimiento')
                    if not pasajero.nombres:
                        pasajero.nombres = final_nombres
                    if not pasajero.apellidos:
                        pasajero.apellidos = final_apellidos
                
                # Guardar la foto del rostro si se obtuvo el recorte
                if foto_recortada:
                    # Borramos la anterior si existe para no llenar el storage de basura
                    if pasajero.foto_id_rostro:
                        pasajero.foto_id_rostro.delete(save=False)
                    pasajero.foto_id_rostro.save(foto_recortada.name, foto_recortada, save=False)
                
                pasajero.save()

            return JsonResponse({
                'status': 'success',
                'created': created,
                'pasajero_id': pasajero.pk,
                'data': {
                    'nombres': pasajero.nombres_ocr,
                    'apellidos': pasajero.apellidos_ocr,
                    'cedula': pasajero.cedula_limpia,
                    'fecha_nacimiento': pasajero.fecha_nacimiento_ocr,
                    'foto_url': pasajero.foto_id_rostro.url if pasajero.foto_id_rostro else None
                }
            })

        except Exception as e:
            logger.error(f"Error guardando pasajero OCR: {e}")
            return JsonResponse({'error': f"Error al persistir datos: {str(e)}"}, status=500)

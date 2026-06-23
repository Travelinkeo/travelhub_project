import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.automation.services.passport_ocr_service import PassportOCRService

logger = logging.getLogger(__name__)


class OCRPassportView(LoginRequiredMixin, View):
    """
    API endpoint para procesar imágenes de pasaporte.
    POST /api/ocr/passport/
    """

    def post(self, request, *args, **kwargs):
        # Aceptamos tanto 'archivo' (Legacy/GDS) como 'archivo_identidad' (Nuevo Dashboard)
        archivo = request.FILES.get("archivo") or request.FILES.get("archivo_identidad")

        if not archivo:
            return JsonResponse(
                {"success": False, "error": "No se proporcionó ningún archivo de imagen."},
                status=400,
            )

        try:
            service = PassportOCRService()
            result = service.process_passport_image(archivo)

            if result["success"]:
                return JsonResponse(
                    {
                        "success": True,
                        "status": "success",  # Para compatibilidad con el nuevo dashboard
                        "data": result["data"],
                        "message": "Pasaporte procesado exitosamente",
                    }
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "error": result.get("error", "Error desconocido al procesar"),
                    },
                    status=500,
                )

        except Exception as e:
            logger.error(f"Error interno OCR: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)

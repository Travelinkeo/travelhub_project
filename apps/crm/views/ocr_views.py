"""Vistas (views) de la aplicación crm.
"""

import base64
import logging

from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from apps.crm.forms import PasajeroForm
from apps.crm.views.pasajeros_views import CRMBaseMixin

logger = logging.getLogger(__name__)


class PasajeroOCRProcessView:
    """Vista para gestionar pasajeroocrprocess. Uso: instanciar según necesidad del dominio.
    """
    def post(self, request, *args, **kwargs):
        # post: Post. Args: según implementación. Returns: según implementación.
        if "archivo" not in request.FILES:
            return HttpResponse(
                "<div class='p-4 text-red-500'>Error: No se recibió ningún archivo.</div>",
                status=400,
            )

        archivo = request.FILES["archivo"]

        try:
            file_content = archivo.read()
            mime_type = archivo.content_type or "image/jpeg"
            from django.utils.module_loading import import_string

            ocr_service = import_string("apps.automation.services.ocr_service.ocr_service")
            result = ocr_service.procesar_pasaporte(file_content, mime_type)

            if result.get("success"):
                data = result
                initial_data = {
                    "nombres": data.get("nombres", ""),
                    "apellidos": data.get("apellidos", ""),
                    "numero_pasaporte": data.get("numero_pasaporte", ""),
                    "fecha_nacimiento": data.get("fecha_nacimiento", ""),
                    "fecha_vencimiento_documento": data.get("fecha_vencimiento", ""),
                    "nacionalidad": data.get("nacionalidad", ""),
                    "pais_emision_documento": data.get("pais_emision", ""),
                    "genero": data.get("sexo", ""),
                }
                form = PasajeroForm(initial=initial_data)
                return render(
                    request,
                    "crm/pasajero_ocr_verification.html",
                    {
                        "form": form,
                        "image_data": data.get("face_image_base64", ""),
                        "confidence": "Alta (>95%)",
                    },
                )
            else:
                return HttpResponse(
                    f"<div class='p-4 text-red-500'>Error del OCR: {result.get('error', 'Desconocido')}</div>",
                    status=400,
                )
        except Exception as e:
            return HttpResponse(
                f"<div class='p-4 text-red-500'>Error Interno: {str(e)}</div>", status=500
            )


class PasajeroOCRSaveView:
    """Vista para gestionar pasajeroocrsave. Uso: instanciar según necesidad del dominio.
    """
    def post(self, request, *args, **kwargs):
        # post: Post. Args: según implementación. Returns: según implementación.
        form = PasajeroForm(request.POST)
        if form.is_valid():
            pasajero = form.save(commit=False)
            pasajero.agencia = getattr(request.user, "agencia", None)
            image_data = request.POST.get("image_data", "")
            if image_data and image_data.startswith("data:image"):
                try:
                    format, imgstr = image_data.split(";base64,")
                    ext = format.split("/")[-1]
                    file_name = f"{pasajero.numero_documento}_perfil.{ext}"
                    pasajero.foto_perfil = ContentFile(base64.b64decode(imgstr), name=file_name)
                except Exception as e:
                    logger.error(f"Error procesando la foto del OCR: {str(e)}")
            pasajero.save()
            messages.success(
                request,
                f"Pasajero {pasajero.get_nombre_completo()} validado y guardado correctamente.",
            )
            response = HttpResponse()
            response["HX-Redirect"] = reverse_lazy("crm:pasajero_list")
            return response
        else:
            return render(
                request,
                "crm/pasajero_ocr_verification.html",
                {
                    "form": form,
                    "image_data": request.POST.get("image_data", ""),
                    "confidence": "Alta (>95%)",
                },
            )

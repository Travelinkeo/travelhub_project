import base64
import logging
from datetime import datetime

from django.core.files.base import ContentFile
from django.core.signing import BadSignature, SignatureExpired
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.bookings.models import Venta
from apps.bookings.models.componentes import ServicioAdicionalDetalle
from apps.bookings.services.itinerary_service import ItineraryCryptoService
from apps.common.models import Pais
from apps.crm.models import Pasajero
from core.api import Agencia, agency_context

logger = logging.getLogger(__name__)


def parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


@require_POST
def public_itinerary_ocr_upload(request, token, pasajero_id):
    """
    Procesa la subida del pasaporte del pasajero de forma anónima y segura usando el token criptográfico.
    Llama al motor de IA multimodal (OCR) y devuelve la previsualización de los datos.
    """
    try:
        venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
            token, max_age_days=30
        )
    except (SignatureExpired, BadSignature):
        return HttpResponse(
            "<div class='p-4 text-red-500 text-sm font-semibold'>Error: El enlace ha expirado o no es válido.</div>",
            status=403,
        )

    agencia = get_object_or_404(Agencia, pk=agencia_id)

    with agency_context(agencia):
        try:
            venta = Venta.all_objects.get(pk=venta_id, agencia_id=agencia_id, is_deleted=False)
            pasajero = venta.pasajeros.get(pk=pasajero_id)
        except (Venta.DoesNotExist, Pasajero.DoesNotExist):
            raise Http404("El itinerario o pasajero no existe.")

        if "archivo" not in request.FILES:
            return HttpResponse(
                "<div class='p-4 text-red-500 text-sm font-semibold'>Error: No se recibió ninguna imagen.</div>",
                status=400,
            )

        archivo = request.FILES["archivo"]
        try:
            file_content = archivo.read()
            mime_type = archivo.content_type or "image/jpeg"

            from apps.automation.services.ocr_service import ocr_service

            result = ocr_service.procesar_pasaporte(file_content, mime_type)

            if result.get("success"):
                initial_data = {
                    "nombres": result.get("nombres", ""),
                    "apellidos": result.get("apellidos", ""),
                    "numero_pasaporte": result.get("numero_pasaporte", ""),
                    "fecha_nacimiento": result.get("fecha_nacimiento", ""),
                    "fecha_vencimiento": result.get("fecha_vencimiento", ""),
                    "sexo": result.get("sexo", ""),
                    "nacionalidad": result.get("nacionalidad", ""),
                    "pais_emision": result.get("pais_emision", ""),
                }

                # Intentamos obtener nombres de países para presentarlos mejor en la verificación
                nacionalidad_pais = None
                if initial_data["nacionalidad"]:
                    nacionalidad_pais = Pais.objects.filter(
                        codigo_iso_3__iexact=initial_data["nacionalidad"]
                    ).first()

                pais_emision_pais = None
                if initial_data["pais_emision"]:
                    pais_emision_pais = Pais.objects.filter(
                        codigo_iso_3__iexact=initial_data["pais_emision"]
                    ).first()

                return render(
                    request,
                    "bookings/passenger_portal/partials/ocr_verification.html",
                    {
                        "pasajero": pasajero,
                        "token": token,
                        "data": initial_data,
                        "nacionalidad_pais": nacionalidad_pais,
                        "pais_emision_pais": pais_emision_pais,
                        "face_image_base64": result.get("face_image_base64", ""),
                    },
                )
            else:
                return HttpResponse(
                    f"<div class='p-4 text-red-500 text-sm font-semibold'>Error del OCR: {result.get('error', 'No se pudo leer el pasaporte.')}</div>",
                    status=400,
                )
        except Exception as e:
            logger.error(f"Error procesando OCR en portal de pasajeros: {e}", exc_info=True)
            return HttpResponse(
                f"<div class='p-4 text-red-500 text-sm font-semibold'>Error interno: {str(e)}</div>",
                status=500,
            )


@require_POST
def public_itinerary_ocr_save(request, token, pasajero_id):
    """
    Guarda los datos verificados del pasaporte en el modelo Pasajero.
    """
    try:
        venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
            token, max_age_days=30
        )
    except (SignatureExpired, BadSignature):
        return HttpResponse(
            "<div class='p-4 text-red-500 text-sm font-semibold'>Error: El enlace ha expirado o no es válido.</div>",
            status=403,
        )

    agencia = get_object_or_404(Agencia, pk=agencia_id)

    with agency_context(agencia):
        try:
            venta = Venta.all_objects.get(pk=venta_id, agencia_id=agencia_id, is_deleted=False)
            pasajero = venta.pasajeros.get(pk=pasajero_id)
        except (Venta.DoesNotExist, Pasajero.DoesNotExist):
            raise Http404("El itinerario o pasajero no existe.")

        # Actualizar campos
        pasajero.nombres = request.POST.get("nombres", pasajero.nombres)
        pasajero.apellidos = request.POST.get("apellidos", pasajero.apellidos)
        pasajero.numero_pasaporte = request.POST.get("numero_pasaporte", pasajero.numero_pasaporte)

        dob = parse_date(request.POST.get("fecha_nacimiento"))
        if dob:
            pasajero.fecha_nacimiento = dob

        expiry = parse_date(request.POST.get("fecha_vencimiento"))
        if expiry:
            pasajero.fecha_vencimiento_documento = expiry
            pasajero.fecha_vencimiento_pasaporte = expiry

        gender = request.POST.get("sexo")
        if gender:
            pasajero.genero = gender

        # Resolver país nacionalidad
        nac_iso = request.POST.get("nacionalidad")
        if nac_iso:
            pais = Pais.objects.filter(codigo_iso_3__iexact=nac_iso).first()
            if pais:
                pasajero.nacionalidad = pais

        # Resolver país emisión
        emi_iso = request.POST.get("pais_emision")
        if emi_iso:
            pais = Pais.objects.filter(codigo_iso_3__iexact=emi_iso).first()
            if pais:
                pasajero.pais_emision_documento = pais

        # Guardar foto recortada de la cara
        face_base64 = request.POST.get("face_image_base64")
        if face_base64 and face_base64.startswith("data:image"):
            try:
                format, imgstr = face_base64.split(";base64,")
                ext = format.split("/")[-1]
                file_name = f"pasajero_{pasajero.pk}_rostro.{ext}"
                pasajero.foto_perfil = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception as pic_err:
                logger.error(f"Error guardando foto recortada: {pic_err}")

        pasajero.save()

        # Renderizar la tarjeta del pasajero actualizada
        return render(
            request,
            "bookings/passenger_portal/partials/passenger_card.html",
            {
                "pasajero": pasajero,
                "token": token,
                "success_message": "¡Pasaporte verificado y guardado con éxito!",
            },
        )


@require_POST
def public_itinerary_cross_sell(request, token):
    """
    Crea una solicitud de servicio adicional (Venta Cruzada) en borrador vinculada a la venta.
    """
    try:
        venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
            token, max_age_days=30
        )
    except (SignatureExpired, BadSignature):
        return HttpResponse(
            "<div class='p-4 text-red-500 text-sm font-semibold'>Error: El enlace ha expirado o no es válido.</div>",
            status=403,
        )

    agencia = get_object_or_404(Agencia, pk=agencia_id)

    with agency_context(agencia):
        try:
            venta = Venta.all_objects.get(pk=venta_id, agencia_id=agencia_id, is_deleted=False)
        except Venta.DoesNotExist:
            raise Http404("El itinerario no existe.")

        tipo_servicio = request.POST.get("tipo_servicio", "OTR")
        nombre_pasajero = request.POST.get("nombre_pasajero", "")
        fecha_inicio_str = request.POST.get("fecha_inicio")
        fecha_fin_str = request.POST.get("fecha_fin")
        notas = request.POST.get("notas", "")

        fecha_inicio = parse_date(fecha_inicio_str)
        fecha_fin = parse_date(fecha_fin_str)

        # Si no se pasó nombre del pasajero, intentamos tomar el del primer pasajero de la venta
        if not nombre_pasajero:
            primer_pax = venta.pasajeros.first()
            if primer_pax:
                nombre_pasajero = f"{primer_pax.apellidos}, {primer_pax.nombres}"

        # Mapear tipo de servicio para una bonita descripción
        servicios_map = {
            "SEG": "Seguro de Viaje",
            "AST": "Asistencia de Viaje",
            "SIM": "SIM / E-SIM de Datos",
            "LNG": "Acceso a Lounge VIP",
            "FST": "Fast Track Aeropuerto",
            "OTR": "Alquiler de Auto / Servicio Adicional",
        }
        nombre_servicio = servicios_map.get(tipo_servicio, "Servicio Adicional")

        # Crear el registro de servicio adicional en borrador (costo/precio nulos o cero)
        servicio_adicional = ServicioAdicionalDetalle.objects.create(
            agencia=agencia,
            venta=venta,
            tipo_servicio=tipo_servicio,
            descripcion=f"Solicitud: {nombre_servicio}",
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            nombre_pasajero=nombre_servicio if not nombre_pasajero else nombre_pasajero,
            notas=f"SOLICITADO DESDE EL PORTAL WEB POR EL PASAJERO.\nNotas adicionales: {notas}",
            costo_neto=0.00,
            precio_venta=0.00,
        )

        return HttpResponse(
            f"""
            <div class="p-6 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-2xl text-center space-y-2">
                <p class="text-lg font-bold">✓ ¡Solicitud Recibida!</p>
                <p class="text-xs">Hemos registrado tu solicitud de <strong>{nombre_servicio}</strong> para {nombre_pasajero or "los pasajeros"}.</p>
                <p class="text-[11px] opacity-80">Tu asesor de viajes se pondrá en contacto pronto para cotizar y confirmar.</p>
            </div>
            """
        )

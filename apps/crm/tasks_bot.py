import logging

from celery import shared_task

from apps.communications.services.whatsapp_unified import procesar_mensaje_entrante

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, time_limit=120, soft_time_limit=90)
def whatsapp_ai_task(self, telefono_cliente, nombre_perfil, mensaje_texto, agencia_id=None):
    """whatsapp_ai_task."""
    from core.api import Agencia, agency_context, system_context

    try:
        if agencia_id:
            agencia = Agencia.objects.get(pk=agencia_id)
            ctx = agency_context(agencia)
        else:
            ctx = system_context()

        with ctx:
            logger.info(f"AI Task: Procesando mensaje de {telefono_cliente}")
            return procesar_mensaje_entrante(telefono_cliente, nombre_perfil, mensaje_texto)
    except Exception as e:
        logger.error(
            f"FALLO DE RESILIENCIA: Error procesando WhatsApp ({telefono_cliente}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60) from e


@shared_task(bind=True, max_retries=3, time_limit=180, soft_time_limit=150)
def whatsapp_media_ocr_task(
    self, telefono_cliente, nombre_perfil, media_id, mime_type, agencia_id=None
):
    """whatsapp_media_ocr_task."""
    import requests
    from django.conf import settings
    from django.utils.module_loading import import_string

    ocr_service = import_string("apps.automation.services.ocr_service.ocr_service")
    from apps.communications.services.whatsapp_unified import send_whatsapp_message
    from apps.crm.models import Cliente, Pasajero
    from core.api import Agencia, agency_context, system_context

    logger.info(f"Iniciando OCR de pasaporte vía WhatsApp para {telefono_cliente}")

    agencia = Agencia.objects.filter(id=agencia_id).first() if agencia_id else None

    if agencia_id and agencia:
        ctx = agency_context(agencia)
    else:
        ctx = system_context()

    with ctx:
        token = getattr(settings, "WHATSAPP_TOKEN", None)
        if agencia and hasattr(agencia, "configuracion_api") and agencia.configuracion_api:
            token = agencia.configuracion_api.get("WHATSAPP_TOKEN", token)

        if not token:
            logger.error("No se pudo obtener el WHATSAPP_TOKEN para descargar multimedia.")
            return False

        try:
            url_meta = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url_meta, headers=headers, timeout=20)
            if response.status_code != 200:
                logger.error(f"Error al consultar multimedia en Meta: {response.text}")
                return False

            media_data = response.json()
            download_url = media_data.get("url")
            if not download_url:
                logger.error("La respuesta de Meta no contiene la URL de descarga.")
                return False

            download_response = requests.get(download_url, headers=headers, timeout=60)
            if download_response.status_code != 200:
                logger.error(f"Error al descargar archivo desde Meta: {download_response.text}")
                return False

            file_bytes = download_response.content

            ocr_result = ocr_service.procesar_pasaporte(file_bytes, mime_type)
            if not ocr_result.get("success"):
                logger.error(f"OCR falló para {telefono_cliente}: {ocr_result.get('error')}")
                mensaje_error = "❌ No pudimos procesar la imagen de tu pasaporte de forma automática. Por favor asegúrate de que la foto sea clara y nítida."
                send_whatsapp_message(telefono_cliente, mensaje_error, agencia=agencia)
                return False

            telefono_limpio = telefono_cliente.replace("+", "").strip()
            cliente, _ = Cliente.objects.get_or_create(
                telefono_principal=telefono_limpio,
                defaults={"nombres": nombre_perfil, "agencia": agencia},
            )

            nombres = ocr_result.get("nombres", "").strip().upper()
            apellidos = ocr_result.get("apellidos", "").strip().upper()
            numero_pasaporte = ocr_result.get("numero_pasaporte", "").strip().upper()

            if not numero_pasaporte:
                logger.error("OCR finalizado pero no se encontró un número de pasaporte válido.")
                mensaje_error = "❌ El pasaporte no tiene un número visible o legible. Por favor envíalo de nuevo."
                send_whatsapp_message(telefono_cliente, mensaje_error, agencia=agencia)
                return False

            pasajero = Pasajero.objects.filter(
                numero_pasaporte=numero_pasaporte, agencia=agencia
            ).first()
            if not pasajero:
                pasajero = Pasajero(numero_pasaporte=numero_pasaporte, agencia=agencia)

            pasajero.nombres = nombres
            pasajero.apellidos = apellidos
            if ocr_result.get("fecha_nacimiento"):
                pasajero.fecha_nacimiento = ocr_result.get("fecha_nacimiento")
            if ocr_result.get("fecha_vencimiento"):
                pasajero.fecha_vencimiento_documento = ocr_result.get("fecha_vencimiento")
            if ocr_result.get("sexo"):
                pasajero.genero = ocr_result.get("sexo")
            if ocr_result.get("nacionalidad_id"):
                pasajero.nacionalidad_id = ocr_result.get("nacionalidad_id")
            if ocr_result.get("pais_emision_id"):
                pasajero.pais_emision_documento_id = ocr_result.get("pais_emision_id")

            pasajero.save()

            face_base64 = ocr_result.get("face_image_base64")
            if face_base64 and face_base64.startswith("data:image"):
                try:
                    import base64

                    from django.core.files.base import ContentFile

                    format, imgstr = face_base64.split(";base64,")
                    ext = format.split("/")[-1]
                    file_name = f"{numero_pasaporte}_perfil.{ext}"
                    pasajero.foto_perfil = ContentFile(base64.b64decode(imgstr), name=file_name)
                    pasajero.save()
                except Exception as e_foto:
                    logger.warning(f"No se pudo guardar la foto de perfil del OCR: {e_foto}")

            cliente.pasajeros.add(pasajero)

            nacionalidad_nombre = "No detectada"
            if pasajero.nacionalidad:
                nacionalidad_nombre = pasajero.nacionalidad.nombre

            mensaje_exito = f"""📸 *¡Pasaporte procesado con éxito!*

Hemos registrado tus datos de pasajero en el sistema:
• *Nombre:* {pasajero.nombres} {pasajero.apellidos}
• *Pasaporte:* {numero_pasaporte}
• *Nacionalidad:* {nacionalidad_nombre}
• *F. Nacimiento:* {pasajero.fecha_nacimiento or "No especificada"}
• *F. Expiración:* {pasajero.fecha_vencimiento_documento or "No especificada"}

Si hay algún dato incorrecto, por favor háznoslo saber por este medio.
"""
            send_whatsapp_message(telefono_cliente, mensaje_exito, agencia=agencia)
            logger.info(f"OCR exitoso y notificado para {telefono_cliente}")
            return True

        except Exception as e:
            logger.error(f"Error procesando OCR de pasaporte vía WhatsApp: {e}")
            try:
                send_whatsapp_message(
                    telefono_cliente,
                    "❌ Ocurrió un error al procesar tu pasaporte en nuestros servidores. Un agente revisará tu caso pronto.",
                    agencia=agencia,
                )
            except Exception as exc:
                logger.debug("Ignored exception sending WhatsApp error message: %s", exc)
            raise self.retry(exc=e, countdown=60) from e

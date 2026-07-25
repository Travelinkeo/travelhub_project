"""Servicio de drive uploader para la aplicación communications.
"""

import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

GOOGLE_DRIVE_AVAILABLE = False
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    pass


def init_drive_service():
    # init_drive_service: Init drive service. Args: según implementación. Returns: según implementación.
    if not GOOGLE_DRIVE_AVAILABLE:
        return None
    try:
        if (
            hasattr(settings, "GOOGLE_APPLICATION_CREDENTIALS")
            and settings.GOOGLE_APPLICATION_CREDENTIALS
        ):
            if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                SCOPES = ["https://www.googleapis.com/auth/drive.file"]
                credentials = service_account.Credentials.from_service_account_file(
                    settings.GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES
                )
                return build("drive", "v3", credentials=credentials)
        return None
    except Exception as e:
        logger.warning(f"Google Drive no disponible para esta instancia: {e}")
        return None


def upload_to_drive(drive_service, pdf_path):
    # upload_to_drive: Upload to drive. Args: según implementación. Returns: según implementación.
    if not drive_service:
        return None

    try:
        file_metadata = {"name": os.path.basename(pdf_path), "mimeType": "application/pdf"}
        media = MediaFileUpload(pdf_path, mimetype="application/pdf")

        file = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )

        file_id = file.get("id")

        drive_service.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"}
        ).execute()

        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except Exception as e:
        logger.error(f"❌ Error subiendo a Drive: {e}")
        return None


def enviar_notificacion_whatsapp_drive(
    drive_service, destination, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path
):
    # enviar_notificacion_whatsapp_drive: Envía ar notificacion whatsapp drive. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.whatsapp_unified import enviar_whatsapp

    drive_link = upload_to_drive(drive_service, pdf_path)

    if drive_link:
        mensaje = f"""✈️ *Boleto {sistema} Procesado*

📍 PNR: *{localizador or "N/A"}*
🎫 Boleto: {numero_boleto}
👤 Pasajero: {pasajero or "N/A"}
✈️ Aerolínea: {aerolinea or "N/A"}

📥 Descarga tu PDF:
{drive_link}

_TravelHub - Sistema Automático_"""
    else:
        mensaje = f"""✈️ *Boleto {sistema} Procesado*

📍 PNR: *{localizador or "N/A"}*
🎫 Boleto: {numero_boleto}
👤 Pasajero: {pasajero or "N/A"}

📄 PDF guardado localmente

_TravelHub - Sistema Automático_"""

    return enviar_whatsapp(destination, mensaje)

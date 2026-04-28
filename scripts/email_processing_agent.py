import base64
import json
import logging
import os
from typing import Any

import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.cms_content_generator import generate_promotional_content
from core.gemini import generate_content
from core.knowledge_base_handler import crear_articulo_desde_gemini
from core.models.comunicaciones import ComunicacionProveedor

# --- Configuración del Agente ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')

# Alcances de la API de Gmail. Si se cambian, se debe borrar token.json
# Se necesita 'gmail.modify' para poder marcar los correos como leídos y 'calendar' para gestionar eventos.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/calendar']
SUPPLIER_EMAILS = settings.SUPPLIER_EMAILS


def get_gmail_service() -> Any | None:
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                logging.error(f"Error: No se encontró '{CREDENTIALS_FILE}'. Descárgalo desde tu Google Cloud Console y colócalo en la carpeta /scripts.")
                return None
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    try:
        return build('gmail', 'v1', credentials=creds)
    except HttpError as error:
        logging.error(f'Ocurrió un error al construir el servicio de Gmail: {error}')
        return None

def search_unread_emails(service: Any, sender_emails: list[str]) -> list[dict[str, str]]:
    query = "is:unread (" + " OR ".join([f"from:{email}" for email in sender_emails]) + ")"
    logging.info(f"Ejecutando búsqueda con la consulta: {query}")
    try:
        response = service.users().messages().list(userId='me', q=query).execute()
        messages = response.get('messages', [])
        logging.info(f"Encontrados {len(messages)} correos no leídos de proveedores.")
        return messages
    except HttpError as error:
        logging.error(f'Ocurrió un error al buscar correos: {error}')
        return []

def get_email_content(service: Any, message_id: str) -> dict[str, Any]:
    content = {"body": "", "attachments": [], "subject": "", "from": ""}
    try:
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        payload = msg.get('payload', {})
        headers = payload.get('headers', [])
        parts = payload.get('parts', [])

        for header in headers:
            if header['name'].lower() == 'subject':
                content['subject'] = header['value']
            if header['name'].lower() == 'from':
                content['from'] = header['value']

        def extract_parts(parts_list):
            body_text, attachments_data = "", []
            for part in parts_list:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    if body_data := part.get('body', {}).get('data'):
                        body_text += base64.urlsafe_b64decode(body_data).decode('utf-8', 'ignore')
                elif mime_type == 'text/html':
                    if body_data := part.get('body', {}).get('data'):
                        soup = BeautifulSoup(base64.urlsafe_b64decode(body_data).decode('utf-8', 'ignore'), 'lxml')
                        body_text += soup.get_text(separator='\n', strip=True)
                elif 'attachmentId' in part['body']:
                    if filename := part.get('filename', ''):
                        if filename.lower().endswith('.pdf'):
                            att_id = part['body']['attachmentId']
                            att = service.users().messages().attachments().get(userId='me', messageId=message_id, id=att_id).execute()
                            if pdf_data := att.get('data'):
                                pdf_text = ""
                                with fitz.open(stream=base64.urlsafe_b64decode(pdf_data), filetype="pdf") as doc:
                                    for page in doc:
                                        pdf_text += page.get_text()
                                attachments_data.append({"filename": filename, "text": pdf_text})
                if 'parts' in part:
                    nested_body, nested_attachments = extract_parts(part['parts'])
                    body_text += nested_body
                    attachments_data.extend(nested_attachments)
            return body_text, attachments_data

        content["body"], content["attachments"] = extract_parts(parts if parts else [payload])
        return content
    except HttpError as error:
        logging.error(f'Ocurrió un error al obtener el contenido del correo {message_id}: {error}')
        return content

def analyze_and_classify_with_gemini(email_content: dict[str, Any]) -> str:
    attachments_summary = "\n".join([f"- Archivo: {att['filename']}\n  Contenido: {att['text'][:2000]}..." for att in email_content['attachments']])
    prompt = f"""
    Eres un agente de operaciones para una agencia de viajes. Tu tarea es analizar el siguiente correo electrónico de un proveedor y realizar dos acciones:
    1.  **Clasifícalo**: Asigna una de las siguientes tres categorías de urgencia: [Notificación Urgente], [Información General], [Promoción]. La clasificación debe ser la primera línea de tu respuesta.
    2.  **Extrae la información**: Resume toda la información relevante en un formato JSON estructurado. El JSON debe ser completo y detallado. Para la categoría [Información General], incluye un campo "categoria_sugerida" en el JSON.

    **Contenido del Correo:**
    - **De:** {email_content.get('from', 'No disponible')}
    - **Asunto:** {email_content.get('subject', 'No disponible')}
    - **Cuerpo del Mensaje:**\n{email_content['body']}

    **Contenido de Archivos Adjuntos:**\n{attachments_summary if attachments_summary else "No hay adjuntos."} 

    Por favor, proporciona tu respuesta comenzando con la etiqueta de clasificación en la primera línea, seguida por el bloque de código JSON.
    """
    return generate_content(prompt)

def main():
    logging.info("Iniciando el Agente Autónomo de Operaciones de TravelHub...")
    gmail_service = get_gmail_service()
    if not gmail_service:
        logging.error("No se pudo iniciar el servicio de Gmail. Abortando.")
        return

    unread_messages = search_unread_emails(gmail_service, SUPPLIER_EMAILS)
    if not unread_messages:
        logging.info("No hay correos nuevos de proveedores para procesar.")
        return

    for message in unread_messages:
        msg_id = message['id']
        logging.info(f"--- Procesando Correo ID: {msg_id} ---")
        content = get_email_content(gmail_service, msg_id)
        
        if not content.get("body") and not content.get("attachments"):
            logging.warning(f"El correo {msg_id} parece estar vacío. Saltando.")
            continue
            
        analysis_result = analyze_and_classify_with_gemini(content)
        
        try:
            lines = analysis_result.strip().split('\n', 1)
            classification_raw = lines[0]
            json_str = lines[1]
            if json_str.strip().startswith("```json"):
                json_str = json_str.strip()[7:-3].strip()
            extracted_json = json.loads(json_str)

            if '[Notificación Urgente]' in classification_raw:
                category = ComunicacionProveedor.Categoria.URGENTE
            elif '[Información General]' in classification_raw:
                category = ComunicacionProveedor.Categoria.INFO
            elif '[Promoción]' in classification_raw:
                category = ComunicacionProveedor.Categoria.PROMO
            else:
                category = ComunicacionProveedor.Categoria.OTRO

            comunicacion = ComunicacionProveedor.objects.create(
                remitente=content.get('from', 'Desconocido'),
                asunto=content.get('subject', 'Sin Asunto'),
                categoria=category,
                contenido_extraido=extracted_json,
                cuerpo_completo=content.get('body', '')
            )
            logging.info(f"Correo ID: {msg_id} procesado y guardado en la BD con ID: {comunicacion.id}")

            # --- Lógica de Post-Procesamiento según Categoría ---

            # Si es Información General, guardarlo en la Base de Conocimiento
            if category == ComunicacionProveedor.Categoria.INFO:
                logging.info("Detectada comunicación de tipo [Información General]. Guardando en Base de Conocimiento...")
                crear_articulo_desde_gemini(
                    datos_gemini=extracted_json,
                    categoria=extracted_json.get('categoria_sugerida', 'Información de Proveedores'),
                    fuente=f"Email de {content.get('from', 'Proveedor Desconocido')}"
                )

            # Si la comunicación es urgente, activar el manejador de notificaciones
            elif category == ComunicacionProveedor.Categoria.URGENTE:
                logging.info("Detectada notificación urgente. Se requiere acción manual o un manejador específico.")
                # Asumiendo que existe una función handle_urgent_notification
                # from core.notification_handler import handle_urgent_notification
                # handle_urgent_notification(extracted_json)
                pass # Dejar pass si la función no está lista

            # Si es una promoción, generar contenido de marketing
            elif category == ComunicacionProveedor.Categoria.PROMO:
                logging.info("Detectada comunicación de tipo [Promoción]. Generando contenido de marketing...")
                creative_content = generate_promotional_content(extracted_json)
                if 'error' in creative_content:
                    logging.error(f"Error al generar contenido de marketing: {creative_content.get('error')}")
                else:
                    comunicacion.whatsapp_status = creative_content.get('whatsapp_status')
                    comunicacion.instagram_post = creative_content.get('instagram_post')
                    comunicacion.instagram_reel_idea = creative_content.get('instagram_reel_idea')
                    comunicacion.save()
                    logging.info(f"Contenido de marketing generado y guardado para la comunicación ID: {comunicacion.id}")

            # Marcar correo como leído
            gmail_service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
            logging.info(f"Correo {msg_id} marcado como leído.")

        except (IndexError, json.JSONDecodeError) as e:
            logging.error(f"No se pudo parsear la respuesta de Gemini para el correo {msg_id}: {e}")
        except Exception as e:
            logging.error(f"Error al guardar en la base de datos para el correo {msg_id}: {e}")


if __name__ == '__main__':
    main()
"""
Google Calendar Integration Service.
Sincroniza ventas y eventos de TravelHub con Google Calendar.

Requiere:
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib

Configuración en settings.py:
    GOOGLE_CALENDAR_API_KEY = os.getenv('GOOGLE_CALENDAR_API_KEY')
    GOOGLE_CALENDAR_CREDENTIALS = os.getenv('GOOGLE_CALENDAR_CREDENTIALS')  # Path to credentials.json
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """
    Servicio para integrar con Google Calendar API v3.

    Uso:
        service = GoogleCalendarService()
        event_id = service.create_venta_event(venta)
        service.update_venta_event(event_id, venta)
        service.delete_event(event_id)
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    API_NAME = "calendar"
    API_VERSION = "v3"

    def __init__(self, credentials_path: str | None = None):
        """
        Inicializa el servicio con credenciales de Google.

        Args:
            credentials_path: Ruta al archivo credentials.json
        """
        self.credentials_path = credentials_path or getattr(
            settings, "GOOGLE_CALENDAR_CREDENTIALS", None
        )
        self._service = None

    def _get_service(self):
        """Obtiene o crea el servicio de Google Calendar."""
        if self._service:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None

            # Intentar cargar credenciales existentes
            token_path = getattr(settings, "GOOGLE_CALENDAR_TOKEN", "token.json")
            try:
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            except FileNotFoundError:
                pass

            # Si no hay credenciales válidas, autenticar
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    from google.auth.transport.requests import Request

                    creds.refresh(Request())
                else:
                    if not self.credentials_path:
                        logger.warning("Google Calendar credentials not configured")
                        return None

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Guardar credenciales para futuro uso
                with open(token_path, "w") as token:
                    token.write(creds.to_json())

            self._service = build(self.API_NAME, self.API_VERSION, credentials=creds)
            return self._service

        except ImportError:
            logger.error(
                "Google API client not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )
            return None
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {e}")
            return None

    def create_venta_event(self, venta, calendar_id: str = "primary") -> str | None:
        """
        Crea un evento en Google Calendar para una venta.

        Args:
            venta: Instancia del modelo Venta
            calendar_id: ID del calendario (default: 'primary')

        Returns:
            ID del evento creado o None si falla
        """
        service = self._get_service()
        if not service:
            return None

        try:
            # Construir descripción del evento
            cliente_nombre = venta.cliente.get_nombre_completo() if venta.cliente else "N/A"
            localizador = venta.localizador or f"#{venta.pk}"

            description = f"""
Venta: {localizador}
Cliente: {cliente_nombre}
Estado: {venta.get_estado_display()}
Total: {venta.moneda} {venta.total_venta:.2f}
Canal: {venta.get_canal_origen_display() if hasattr(venta, 'get_canal_origen_display') else venta.canal_origen}

TravelHub - {venta.agencia.nombre if venta.agencia else ''}
            """.strip()

            # Evento de 30 minutos
            start_time = timezone.now()
            end_time = start_time + timedelta(minutes=30)

            event = {
                "summary": f"Venta {localizador} - {cliente_nombre}",
                "description": description,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "America/Caracas",
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "America/Caracas",
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 24 * 60},  # 1 día antes
                        {"method": "popup", "minutes": 30},  # 30 min antes
                    ],
                },
                "extendedProperties": {
                    "private": {
                        "travelhub_venta_id": str(venta.pk),
                        "travelhub_agencia_id": str(venta.agencia_id) if venta.agencia_id else "",
                    }
                },
            }

            created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

            event_id = created_event.get("id")
            logger.info(f"Google Calendar event created for venta {venta.pk}: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"Error creating Google Calendar event for venta {venta.pk}: {e}")
            return None

    def update_venta_event(self, event_id: str, venta, calendar_id: str = "primary") -> bool:
        """
        Actualiza un evento existente en Google Calendar.

        Args:
            event_id: ID del evento a actualizar
            venta: Instancia del modelo Venta
            calendar_id: ID del calendario

        Returns:
            True si se actualizó correctamente
        """
        service = self._get_service()
        if not service:
            return False

        try:
            cliente_nombre = venta.cliente.get_nombre_completo() if venta.cliente else "N/A"
            localizador = venta.localizador or f"#{venta.pk}"

            description = f"""
Venta: {localizador}
Cliente: {cliente_nombre}
Estado: {venta.get_estado_display()}
Total: {venta.moneda} {venta.total_venta:.2f}
Canal: {venta.get_canal_origen_display() if hasattr(venta, 'get_canal_origen_display') else venta.canal_origen}

TravelHub - {venta.agencia.nombre if venta.agencia else ''}
            """.strip()

            event = {
                "summary": f"Venta {localizador} - {cliente_nombre}",
                "description": description,
            }

            service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()

            logger.info(f"Google Calendar event updated for venta {venta.pk}: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating Google Calendar event {event_id}: {e}")
            return False

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """
        Elimina un evento de Google Calendar.

        Args:
            event_id: ID del evento a eliminar
            calendar_id: ID del calendario

        Returns:
            True si se eliminó correctamente
        """
        service = self._get_service()
        if not service:
            return False

        try:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

            logger.info(f"Google Calendar event deleted: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting Google Calendar event {event_id}: {e}")
            return False

    def list_upcoming_events(self, max_results: int = 10, calendar_id: str = "primary") -> list:
        """
        Lista los próximos eventos de Google Calendar.

        Args:
            max_results: Número máximo de eventos a retornar
            calendar_id: ID del calendario

        Returns:
            Lista de eventos
        """
        service = self._get_service()
        if not service:
            return []

        try:
            now = timezone.now().isoformat() + "Z"  # 'Z' indica UTC

            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            return events_result.get("items", [])

        except Exception as e:
            logger.error(f"Error listing Google Calendar events: {e}")
            return []


# ============================================================================
# Helper functions for use in Django views/tasks
# ============================================================================


def sync_venta_to_calendar(venta) -> str | None:
    """
    Sincroniza una venta con Google Calendar.
    Útil para llamar desde señales o tareas Celery.

    Args:
        venta: Instancia del modelo Venta

    Returns:
        ID del evento creado o None
    """
    service = GoogleCalendarService()
    return service.create_venta_event(venta)


def update_venta_in_calendar(event_id: str, venta) -> bool:
    """
    Actualiza una venta en Google Calendar.

    Args:
        event_id: ID del evento en Google Calendar
        venta: Instancia del modelo Venta

    Returns:
        True si se actualizó correctamente
    """
    service = GoogleCalendarService()
    return service.update_venta_event(event_id, venta)


def remove_venta_from_calendar(event_id: str) -> bool:
    """
    Elimina una venta de Google Calendar.

    Args:
        event_id: ID del evento en Google Calendar

    Returns:
        True si se eliminó correctamente
    """
    service = GoogleCalendarService()
    return service.delete_event(event_id)

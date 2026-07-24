"""
Email Unified Service
Consolidated service for all email operations:
- Core sending (Resend API + Django SMTP fallback)
- HTML emails with embedded assets (logo)
- Notification templates (confirmation, payment, status change)
- Email Monitor (IMAP polling for ticket capture)
"""

import email
import imaplib
import logging
import os
import time
from email.mime.image import MIMEImage

import resend
from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1: CORE SENDING (Resend + Django SMTP)
# ============================================================================

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def send_custom_email(
    subject: str,
    recipient: str,
    template_name: str,
    context: dict,
    from_email: str = None,
    agencia=None,
) -> bool:
    """
    Función centralizada que utiliza Resend para el envío de correos.
    Si no hay API Key de Resend, cae de nuevo al send_mail estándar de Django.
    """
    if not recipient:
        return False

    try:
        html_content = render_to_string(template_name, context)
        sender = (
            from_email
            or (agencia.email_principal if agencia else None)
            or "TravelHub <notificaciones@travelhub.cc>"
        )

        if RESEND_API_KEY:
            params = {
                "from": sender,
                "to": [recipient],
                "subject": subject,
                "html": html_content,
            }
            resend.Emails.send(params)
            logger.info(f"✨ Email enviado vía RESEND API: {subject} a {recipient}")
        else:
            text_content = strip_tags(html_content)
            connection = None
            if agencia:
                email_config = agencia.configuracion_correo
                if email_config and email_config.get("EMAIL_HOST"):
                    try:
                        from django.core.mail import get_connection

                        connection = get_connection(
                            host=email_config.get("EMAIL_HOST"),
                            port=email_config.get("EMAIL_PORT", 587),
                            username=email_config.get("EMAIL_HOST_USER"),
                            password=email_config.get("EMAIL_HOST_PASSWORD"),
                            use_tls=email_config.get("EMAIL_USE_TLS", True),
                        )
                        sender = (
                            sender
                            or email_config.get("DEFAULT_FROM_EMAIL")
                            or email_config.get("EMAIL_HOST_USER")
                        )
                    except Exception as smtp_err:
                        logger.error(
                            f"Error establishing dynamic SMTP connection for agency {agencia.nombre}: {smtp_err}"
                        )

            if connection:
                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=sender,
                    to=[recipient],
                    connection=connection,
                )
                email_msg.attach_alternative(html_content, "text/html")
                email_msg.send(fail_silently=False)
            else:
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=sender,
                    recipient_list=[recipient],
                    html_message=html_content,
                    fail_silently=False,
                )
            logger.info(f"📧 Email enviado vía Django SMTP: {subject} a {recipient}")

        return True
    except Exception as e:
        logger.error(f"❌ Error crítico enviando email: {str(e)}")
        return False


def enviar_email_generico(
    destinatario: str, asunto: str, mensaje: str, from_email: str = None, agencia=None
) -> bool:
    """Envía un email simple en formato texto/html"""
    try:
        sender = (
            from_email
            or (agencia.email_principal if agencia else None)
            or settings.DEFAULT_FROM_EMAIL
        )

        connection = None
        if agencia:
            email_config = agencia.configuracion_correo
            if email_config and email_config.get("EMAIL_HOST"):
                try:
                    from django.core.mail import get_connection

                    connection = get_connection(
                        host=email_config.get("EMAIL_HOST"),
                        port=email_config.get("EMAIL_PORT", 587),
                        username=email_config.get("EMAIL_HOST_USER"),
                        password=email_config.get("EMAIL_HOST_PASSWORD"),
                        use_tls=email_config.get("EMAIL_USE_TLS", True),
                    )
                    sender = (
                        sender
                        or email_config.get("DEFAULT_FROM_EMAIL")
                        or email_config.get("EMAIL_HOST_USER")
                    )
                except Exception as smtp_err:
                    logger.error(
                        f"Error establishing dynamic SMTP connection for agency {agencia.nombre}: {smtp_err}"
                    )

        email_msg = EmailMultiAlternatives(
            asunto, mensaje, sender, [destinatario], connection=connection
        )
        if "<" in mensaje and ">" in mensaje:
            email_msg.attach_alternative(mensaje, "text/html")

        email_msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Error enviando email genérico: {e}")
        return False


def enviar_email_html(
    asunto: str,
    template_name: str,
    context: dict,
    destinatario: str,
    from_email: str = None,
    agencia=None,
    adjuntos=None,
) -> bool:
    """Función auxiliar para enviar emails HTML con logo embebido y opcionalmente adjuntos"""
    try:
        html_content = render_to_string(template_name, context)
        sender = (
            from_email
            or (agencia.email_principal if agencia else None)
            or settings.DEFAULT_FROM_EMAIL
        )

        connection = None
        if agencia:
            email_config = agencia.configuracion_correo
            if email_config and email_config.get("EMAIL_HOST"):
                try:
                    from django.core.mail import get_connection

                    connection = get_connection(
                        host=email_config.get("EMAIL_HOST"),
                        port=email_config.get("EMAIL_PORT", 587),
                        username=email_config.get("EMAIL_HOST_USER"),
                        password=email_config.get("EMAIL_HOST_PASSWORD"),
                        use_tls=email_config.get("EMAIL_USE_TLS", True),
                    )
                    sender = (
                        sender
                        or email_config.get("DEFAULT_FROM_EMAIL")
                        or email_config.get("EMAIL_HOST_USER")
                    )
                except Exception as smtp_err:
                    logger.error(
                        f"Error establishing dynamic SMTP connection for agency {agencia.nombre}: {smtp_err}"
                    )

        email_msg = EmailMultiAlternatives(
            asunto,
            f"Este email requiere un cliente que soporte HTML. Contenido: {context.get('localizador', '')}",
            sender,
            [destinatario],
            connection=connection,
        )
        email_msg.attach_alternative(html_content, "text/html")

        # Adjuntar logo como imagen embebida
        logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo-blanco.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_data = f.read()
                logo_image = MIMEImage(logo_data)
                logo_image.add_header("Content-ID", "<logo>")
                logo_image.add_header("Content-Disposition", "inline", filename="logo-blanco.png")
                email_msg.attach(logo_image)

        # Adjuntar archivos adicionales (PDFs, etc.)
        if adjuntos:
            for adjunto in adjuntos:
                if isinstance(adjunto, dict):
                    archivo = adjunto.get("archivo")
                    nombre = adjunto.get("nombre", "archivo.pdf")
                else:
                    archivo = adjunto
                    nombre = os.path.basename(str(adjunto))

                if archivo and os.path.exists(str(archivo)):
                    try:
                        with open(str(archivo), "rb") as f:
                            email_msg.attach(nombre, f.read(), "application/pdf")
                    except Exception as adj_err:
                        logger.warning(f"Error adjuntando archivo {nombre}: {adj_err}")

        email_msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Error enviando email HTML: {e}")
        return False


# ============================================================================
# SECTION 2: NOTIFICATION TEMPLATES
# ============================================================================


def enviar_confirmacion_venta(venta) -> bool:
    """Envía email de confirmación de venta al cliente con factura adjunta si existe"""
    if not venta.cliente or not venta.cliente.email:
        logger.warning(
            f"No se puede enviar confirmación para venta {venta.id_venta}: cliente sin email"
        )
        return False

    agencia = getattr(venta, "agencia", None)
    nombre_agencia = agencia.nombre_comercial or agencia.nombre if agencia else "TravelHub"
    from_email = agencia.email_principal if agencia else None

    context = {
        "venta": venta,
        "cliente": venta.cliente,
        "items": venta.items_venta.all(),
        "cliente_nombre": venta.cliente.get_nombre_completo(),
        "localizador": venta.localizador,
        "fecha": venta.fecha_venta.strftime("%d/%m/%Y"),
        "total": venta.total_venta,
        "moneda": venta.moneda.simbolo if venta.moneda else "",
        "estado": venta.get_estado_display(),
        "nombre_agencia": nombre_agencia,
    }

    # Buscar factura asociada para adjuntar PDF
    adjuntos = []
    try:
        Factura = apps.get_model("finance", "Factura")

        factura = Factura.objects.filter(venta_asociada=venta).first()
        if factura and factura.archivo_pdf:
            try:
                pdf_path = factura.archivo_pdf.path
                adjuntos.append(
                    {"archivo": pdf_path, "nombre": f"Factura_{factura.numero_factura}.pdf"}
                )
            except (NotImplementedError, ValueError):
                pass
    except Exception as e:
        logger.debug(f"No se encontró factura para venta {venta.id_venta}: {e}")

    resultado = enviar_email_html(
        f"[{nombre_agencia}] Confirmación de Reserva - {venta.localizador}",
        "core/emails/confirmacion_venta.html",
        context,
        venta.cliente.email,
        from_email=from_email,
        agencia=agencia,
        adjuntos=adjuntos if adjuntos else None,
    )

    if resultado:
        logger.info(
            f"Email confirmación enviado para venta {venta.id_venta} (Agencia: {nombre_agencia})"
        )
    return resultado


def enviar_recordatorio_pago(venta) -> bool:
    """Envía recordatorio de pago pendiente con factura adjunta si existe"""
    if not venta.cliente or not venta.cliente.email:
        return False

    if venta.saldo_pendiente <= 0:
        return False

    agencia = getattr(venta, "agencia", None)
    nombre_agencia = agencia.nombre_comercial or agencia.nombre if agencia else "TravelHub"
    from_email = agencia.email_principal if agencia else None

    context = {
        "venta": venta,
        "cliente": venta.cliente,
        "saldo_pendiente": venta.saldo_pendiente,
        "cliente_nombre": venta.cliente.get_nombre_completo(),
        "localizador": venta.localizador,
        "total": venta.total_venta,
        "pagado": venta.total_venta - venta.saldo_pendiente,
        "saldo": venta.saldo_pendiente,
        "moneda": venta.moneda.simbolo if venta.moneda else "",
        "nombre_agencia": nombre_agencia,
    }

    adjuntos = []
    try:
        Factura = apps.get_model("finance", "Factura")

        factura = Factura.objects.filter(venta_asociada=venta).first()
        if factura and factura.archivo_pdf:
            try:
                pdf_path = factura.archivo_pdf.path
                adjuntos.append(
                    {"archivo": pdf_path, "nombre": f"Factura_{factura.numero_factura}.pdf"}
                )
            except (NotImplementedError, ValueError):
                pass
    except Exception as e:
        logger.debug(f"No se encontró factura para venta {venta.id_venta}: {e}")

    resultado = enviar_email_html(
        f"[{nombre_agencia}] Recordatorio de Pago - {venta.localizador}",
        "core/emails/recordatorio_pago.html",
        context,
        venta.cliente.email,
        from_email=from_email,
        agencia=agencia,
        adjuntos=adjuntos if adjuntos else None,
    )

    if resultado:
        logger.info(f"Email recordatorio pago enviado para venta {venta.id_venta}")
    return resultado


def enviar_cambio_estado(venta, estado_anterior: str) -> bool:
    """Envía notificación de cambio de estado con factura adjunta si aplica"""
    if not venta.cliente or not venta.cliente.email:
        return False

    agencia = getattr(venta, "agencia", None)
    nombre_agencia = agencia.nombre_comercial or agencia.nombre if agencia else "TravelHub"
    from_email = agencia.email_principal if agencia else None

    context = {
        "venta": venta,
        "cliente": venta.cliente,
        "estado_anterior": estado_anterior,
        "estado_actual": venta.get_estado_display(),
        "cliente_nombre": venta.cliente.get_nombre_completo(),
        "localizador": venta.localizador,
        "nombre_agencia": nombre_agencia,
    }

    adjuntos = []
    if venta.estado in ["PAG", "PPA"]:
        try:
            Factura = apps.get_model("finance", "Factura")

            factura = Factura.objects.filter(venta_asociada=venta).first()
            if factura and factura.archivo_pdf:
                try:
                    pdf_path = factura.archivo_pdf.path
                    adjuntos.append(
                        {"archivo": pdf_path, "nombre": f"Factura_{factura.numero_factura}.pdf"}
                    )
                except (NotImplementedError, ValueError):
                    pass
        except Exception as e:
            logger.debug(f"No se encontró factura para venta {venta.id_venta}: {e}")

    resultado = enviar_email_html(
        f"[{nombre_agencia}] Actualización de Reserva - {venta.localizador}",
        "core/emails/cambio_estado.html",
        context,
        venta.cliente.email,
        from_email=from_email,
        agencia=agencia,
        adjuntos=adjuntos if adjuntos else None,
    )

    if resultado:
        logger.info(f"Email cambio estado enviado para venta {venta.id_venta}")
    return resultado


def enviar_confirmacion_pago(pago_venta) -> bool:
    """Envía confirmación cuando se registra un pago"""
    venta = pago_venta.venta
    if not venta.cliente or not venta.cliente.email:
        return False

    agencia = getattr(venta, "agencia", None)
    nombre_agencia = agencia.nombre_comercial or agencia.nombre if agencia else "TravelHub"
    from_email = agencia.email_principal if agencia else None

    context = {
        "cliente_nombre": venta.cliente.get_nombre_completo(),
        "localizador": venta.localizador,
        "monto": pago_venta.monto,
        "fecha": pago_venta.fecha_pago.strftime("%d/%m/%Y"),
        "metodo": pago_venta.get_metodo_display(),
        "saldo": venta.saldo_pendiente,
        "moneda": pago_venta.moneda.simbolo if pago_venta.moneda else "",
        "nombre_agencia": nombre_agencia,
    }

    resultado = enviar_email_html(
        f"[{nombre_agencia}] Confirmación de Pago - {venta.localizador}",
        "core/emails/confirmacion_pago.html",
        context,
        venta.cliente.email,
        from_email=from_email,
        agencia=agencia,
    )

    if resultado:
        logger.info(f"Email confirmación pago enviado para venta {venta.id_venta}")
    return resultado


# ============================================================================
# SECTION 3: EMAIL MONITOR (IMAP Polling for Ticket Capture)
# ============================================================================

PYPDF_AVAILABLE = False
try:
    import pypdf

    PYPDF_AVAILABLE = True
except ImportError:
    logger.warning("pypdf no instalado")

GOOGLE_DRIVE_AVAILABLE = False
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    pass


class EmailMonitorService:
    """Monitor unificado de correos con múltiples canales de notificación"""

    def __init__(
        self,
        agencia,
        notification_type: str = "whatsapp",
        destination=None,
        interval: int = 60,
        mark_as_read: bool = False,
        process_all: bool = False,
        force_reprocess: bool = False,
    ):
        """
        Args:
            agencia: Instancia de Agencia (con credenciales)
            notification_type: 'whatsapp', 'email', 'whatsapp_drive', 'telegram'
            destination: Número de teléfono o email destino
            interval: Segundos entre verificaciones
            mark_as_read: Marcar correos como leídos
            process_all: Procesar todos los correos (incluso leídos)
            force_reprocess: Reprocesar boletos existentes
        """
        self.agencia = agencia
        self.notification_type = notification_type
        self.destination = (
            destination
            or getattr(agencia, "whatsapp", None)
            or getattr(agencia, "email_ventas", None)
        )
        self.interval = interval
        self.mark_as_read = mark_as_read
        self.process_all = process_all
        self.force_reprocess = force_reprocess
        self.drive_service = None

        if notification_type == "whatsapp_drive" and GOOGLE_DRIVE_AVAILABLE:
            self.drive_service = self._init_drive()

    def _init_drive(self):
        """Inicializa servicio de Google Drive"""
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

    def procesar_una_vez(self):
        """Procesa correos una sola vez y retorna cantidad procesada"""
        logger.info(
            f"🔍 Procesando correos una vez -> {self.notification_type}: {self.destination}"
        )
        return self._procesar_correos()

    def start(self):
        """Inicia el monitoreo continuo"""
        logger.info(f"🚀 Monitor iniciado -> {self.notification_type}: {self.destination}")

        while True:
            try:
                self._procesar_correos()
            except Exception as e:
                logger.error(f"❌ Error en ciclo: {e}")

            time.sleep(self.interval)

    def _actualizar_last_check(self):
        """Actualiza el timestamp del último chequeo exitoso en la configuración"""
        try:
            from django.utils import timezone

            config = getattr(self.agencia, "configuracion", None)
            if config:
                config.email_monitor_last_check = timezone.now()
                config.save(update_fields=["email_monitor_last_check"])
        except Exception as e:
            logger.warning(f"⚠️ No se pudo actualizar email_monitor_last_check: {e}")

    def _procesar_correos(self):
        """Procesa correos no leídos, registra ejecución en EmailMonitorLog y retorna cantidad procesada"""
        inicio = time.time()
        imap_host = "imap.gmail.com"
        imap_port = 993

        try:
            from apps.communications.models import EmailMonitorLog

            config = getattr(self.agencia, "configuracion", None)

            imap_user = getattr(config, "email_monitor_user", None) or getattr(
                self.agencia, "correo_emisiones", None
            )
            imap_pass = getattr(config, "email_monitor_password", None) or getattr(
                self.agencia, "password_app_correo", None
            )

            if not imap_user or not imap_pass:
                msg = f"Agencia {self.agencia.nombre} no tiene credenciales de correo configuradas."
                logger.warning(f"⚠️ {msg}")
                EmailMonitorLog.objects.create(
                    agencia=self.agencia,
                    estado=EmailMonitorLog.Estado.WARNING,
                    mensaje=msg,
                    host_conectado=None,
                    correos_procesados=0,
                    tiempo_ejecucion=round(time.time() - inicio, 2),
                )
                return 0

            imap_host = (
                getattr(config, "email_monitor_host", "imap.gmail.com")
                if config
                else "imap.gmail.com"
            )
            imap_port = getattr(config, "email_monitor_port", 993) if config else 993
            if not imap_host:
                imap_host = "imap.gmail.com"
            if not imap_port:
                imap_port = 993

            try:
                mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            except Exception as e_conn:
                msg = f"Error conectando al servidor IMAP {imap_host}:{imap_port}: {e_conn}"
                logger.error(f"❌ {msg}")
                EmailMonitorLog.objects.create(
                    agencia=self.agencia,
                    estado=EmailMonitorLog.Estado.ERROR,
                    mensaje=msg,
                    host_conectado=f"{imap_host}:{imap_port}",
                    correos_procesados=0,
                    tiempo_ejecucion=round(time.time() - inicio, 2),
                )
                return 0

            try:
                mail.login(imap_user, imap_pass)
            except Exception as e:
                msg = (
                    f"Error de autenticación IMAP para {imap_user} en {imap_host}:{imap_port}: {e}"
                )
                logger.error(f"❌ {msg}")
                EmailMonitorLog.objects.create(
                    agencia=self.agencia,
                    estado=EmailMonitorLog.Estado.ERROR,
                    mensaje=msg,
                    host_conectado=f"{imap_host}:{imap_port}",
                    correos_procesados=0,
                    tiempo_ejecucion=round(time.time() - inicio, 2),
                )
                return 0

            select_status, _ = mail.select("inbox")
            if select_status != "OK":
                msg = f"No se pudo seleccionar inbox en {imap_host}:{imap_port}"
                logger.error(f"❌ {msg}")
                mail.logout()
                EmailMonitorLog.objects.create(
                    agencia=self.agencia,
                    estado=EmailMonitorLog.Estado.ERROR,
                    mensaje=msg,
                    host_conectado=f"{imap_host}:{imap_port}",
                    correos_procesados=0,
                    tiempo_ejecucion=round(time.time() - inicio, 2),
                )
                return 0

            if self.process_all:
                _, messages = mail.search(None, "ALL")
                logger.info("📦 Procesando TODOS los correos")
            else:
                _, messages = mail.search(None, "(UNSEEN)")
                logger.info("🆕 Procesando solo correos NO LEÍDOS")

            message_ids = messages[0].split()

            if not message_ids:
                logger.info("📭 No hay correos nuevos")
                mail.close()
                mail.logout()
                EmailMonitorLog.objects.create(
                    agencia=self.agencia,
                    estado=EmailMonitorLog.Estado.SUCCESS,
                    mensaje="Ciclo completado. No se encontraron correos nuevos.",
                    host_conectado=f"{imap_host}:{imap_port}",
                    correos_procesados=0,
                    tiempo_ejecucion=round(time.time() - inicio, 2),
                )
                self._actualizar_last_check()
                return 0

            logger.info(f"📬 Encontrados {len(message_ids)} correos nuevos")
            procesados = 0

            for num in message_ids:
                try:
                    _, msg_data = mail.fetch(num, "(RFC822)")
                    message = email.message_from_bytes(msg_data[0][1])

                    if self._procesar_mensaje(message, num, mail):
                        logger.info(f"✅ Correo {num} procesado")
                        procesados += 1
                except Exception as e:
                    logger.error(f"❌ Error procesando {num}: {e}")

            mail.close()
            mail.logout()

            EmailMonitorLog.objects.create(
                agencia=self.agencia,
                estado=EmailMonitorLog.Estado.SUCCESS,
                mensaje=f"Ciclo completado. {procesados} de {len(message_ids)} correos procesados exitosamente.",
                host_conectado=f"{imap_host}:{imap_port}",
                correos_procesados=procesados,
                tiempo_ejecucion=round(time.time() - inicio, 2),
            )
            self._actualizar_last_check()
            return procesados

        except Exception as e_global:
            msg = f"Error inesperado en el ciclo de monitoreo: {e_global}"
            logger.exception(f"❌ {msg}")
            try:
                if "mail" in locals() and mail is not None:
                    try:
                        mail.close()
                    except Exception as e_close:
                        logger.debug(f"Error closing IMAP connection: {e_close}")
                    try:
                        mail.logout()
                    except Exception as e_logout:
                        logger.debug(f"Error logging out IMAP connection: {e_logout}")
            except Exception as e_cleanup:
                logger.debug(f"Error during IMAP cleanup: {e_cleanup}")
            try:
                from apps.communications.models import EmailMonitorLog

                EmailMonitorLog.objects.create(
                    agencia=self.agencia,
                    estado=EmailMonitorLog.Estado.ERROR,
                    mensaje=msg,
                    host_conectado=f"{imap_host}:{imap_port}" if imap_host else None,
                    correos_procesados=0,
                    tiempo_ejecucion=round(time.time() - inicio, 2),
                )
            except Exception as e_log:
                logger.debug(f"Error logging monitor error to EmailMonitorLog: {e_log}")
            return 0

    def _procesar_mensaje(self, message, msg_num, mail_connection):
        """Procesa un mensaje individual"""
        subject = message.get("Subject", "")
        from_addr = message.get("From", "")

        if subject and subject.startswith("=?"):
            try:
                import email.header

                decoded = email.header.decode_header(subject)
                subject = "".join(
                    [
                        str(t[0], t[1] or "utf-8") if isinstance(t[0], bytes) else t[0]
                        for t in decoded
                    ]
                )
            except Exception as e:
                logger.warning(f"Excepción silenciosa capturada: {e}")
        logger.info(f"Procesando: {subject[:50]}...")
        logger.info(f"De: {from_addr}")

        subject_upper = subject.upper() if subject else ""
        from_lower = from_addr.lower() if from_addr else ""

        tiene_pdf = self._tiene_pdf_adjunto(message)
        logger.info(f"PDF adjunto: {tiene_pdf}")

        if tiene_pdf:
            logger.info("Procesando PDF adjunto...")

            # 1. Intentar procesar como Reporte de Ventas de Proveedor (CTG, MY DESTINY, etc.)
            try:
                from apps.contabilidad.supplier_report_service import SupplierReportProcessorService

                for part in message.walk():
                    fn = part.get_filename()
                    if fn and fn.lower().endswith(".pdf"):
                        pdf_data = part.get_payload(decode=True)
                        if pdf_data:
                            reporte = SupplierReportProcessorService.procesar_pdf_reporte(
                                pdf_bytes=pdf_data,
                                filename=fn,
                                subject=subject,
                                sender_email=from_addr,
                                agencia=self.agencia,
                            )
                            if reporte:
                                logger.info(
                                    f"✅ Reporte de proveedor {reporte.proveedor_nombre} "
                                    f"procesado desde Email Monitor para {self.agencia.nombre}."
                                )
                                if self.mark_as_read and mail_connection:
                                    mail_connection.store(msg_num, "+FLAGS", "\\Seen")
                                return True
            except Exception as e_sup:
                logger.debug(f"Email no es reporte de proveedor o falló parseo: {e_sup}")

            # 2. Procesamiento estándar de boletos de avión individuales en PDF
            if self._procesar_boleto_pdf(message, msg_num, mail_connection):
                if self.mark_as_read and mail_connection:
                    mail_connection.store(msg_num, "+FLAGS", "\\Seen")
                return True
            logger.warning("⚠️ Falló el procesamiento del PDF, intentando fallback a HTML...")

        is_kiu_subject = (
            "E-TICKET ITINERARY RECEIPT" in subject_upper
            or "ETICKET ITINERARY RECEIPT" in subject_upper
            or "PASSENGER ITINERARY RECEIPT" in subject_upper
            or "TICKETS AVIOR" in subject_upper
            or "AVIOR AIRLINES" in subject_upper
            or "LASER AIRLINES" in subject_upper
            or "RUTACA" in subject_upper
            or "VENEZOLANA" in subject_upper
        )

        is_official_kiu = "kiusys.com" in from_lower

        logger.info(f"Es KIU Oficial: {is_official_kiu} | Subject Ticket: {is_kiu_subject}")

        if is_official_kiu:
            logger.info("Procesando KIU Oficial (HTML)")
            resultado = self._procesar_boleto_email(message, msg_num, mail_connection)
            if resultado and self.mark_as_read and mail_connection:
                mail_connection.store(msg_num, "+FLAGS", "\\Seen")
            return resultado

        # ⚡ Interceptación Autónoma para PNR GDS (Amadeus, Sabre, KIU)
        texto = self._extraer_texto(message)
        html = self._extraer_html(message)
        email_body = texto
        if not email_body and html:
            email_body = strip_tags(html)

        if email_body:
            from django.utils.module_loading import import_string

            PNRParserService = import_string(
                "apps.bookings.services.pnr_parser_service.PNRParserService"
            )

            gds_detected = PNRParserService.detectar_gds(email_body)
            if gds_detected != "GENERIC":
                logger.info(
                    f"⚡ PNR GDS detectado en email ({gds_detected}). Ingestando autónomamente..."
                )
                try:
                    venta = PNRParserService.ingerir_pnr_en_db(email_body, self.agencia)
                    logger.info(
                        f"✅ Ingestión exitosa: Venta {venta.localizador} creada desde Email Parsing Autónomo."
                    )
                    if self.mark_as_read and mail_connection:
                        mail_connection.store(msg_num, "+FLAGS", "\\Seen")
                    return True
                except ValueError as ve:
                    try:
                        import sentry_sdk

                        with sentry_sdk.push_scope() as scope:
                            scope.set_tag("app_module", "gds_parser")
                            scope.set_tag("gds_system", gds_detected)
                            scope.set_tag("agencia_id", self.agencia.pk)
                            scope.set_tag(
                                "agencia_subdominio", getattr(self.agencia, "subdominio", "unknown")
                            )

                            scope.set_extra("pnr_raw_payload", email_body)
                            scope.set_extra("error_details", str(ve))

                            sentry_sdk.capture_exception(ve)
                    except ImportError:
                        pass
                    logger.error(
                        f"Fallo crítico de parsing PNR para Agencia [{self.agencia.pk}]. Sistema GDS: {gds_detected}.",
                        extra={
                            "agencia_id": self.agencia.pk,
                            "gds": gds_detected,
                            "raw_payload": email_body,
                        },
                    )
                except Exception as e:
                    try:
                        import sentry_sdk

                        with sentry_sdk.push_scope() as scope:
                            scope.set_tag("app_module", "email_monitor_critical")
                            scope.set_tag("agencia_id", self.agencia.pk)
                            sentry_sdk.capture_exception(e)
                    except ImportError:
                        pass
                    logger.error(f"❌ Error en parseo autónomo de email GDS: {e}")

        if is_kiu_subject:
            logger.info("Procesando como KIU/HTML por Asunto")
            resultado = self._procesar_boleto_email(message, msg_num, mail_connection)
            if resultado and self.mark_as_read and mail_connection:
                mail_connection.store(msg_num, "+FLAGS", "\\Seen")
            return resultado

        logger.warning("No reconocido como boleto")
        return False

    def _procesar_boleto_email(self, message, msg_num, mail_connection):
        """Procesa boleto desde HTML/texto del correo usando TicketParserService"""
        try:
            logger.info("📩 Procesando Email (Body/HTML)...")
            from django.apps import apps
            from django.core.files.base import ContentFile

            BoletoImportado = apps.get_model("bookings", "BoletoImportado")

            texto = self._extraer_texto(message)
            html = self._extraer_html(message)

            if not texto and not html:
                logger.warning("No hay contenido en el mensaje")
                return False

            content = html if html else texto
            ext = "html" if html else "txt"
            filename = f"email_ticket_{msg_num}.{ext}"

            boleto = BoletoImportado(
                agencia=self.agencia,
                estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                formato_detectado="EMAIL_AUTO",
                log_parseo="",
                numero_boleto="",
                nombre_pasajero_completo="",
                nombre_pasajero_procesado="",
                localizador_pnr="",
                ruta_vuelo="",
                aerolinea_emisora="",
                direccion_aerolinea="",
                agente_emisor="",
                foid_pasajero="",
                impuestos_descripcion="",
                telegram_file_id="",
                raw_hash="",
                datos_parseados={},
            )
            boleto.archivo_boleto.save(filename, ContentFile(content.encode("utf-8")))
            boleto.save()
            logger.info(f"📁 BoletoImportado creado: ID {boleto.pk}")

            from apps.bookings.tasks import parsear_boleto_individual

            parsear_boleto_individual.delay(boleto.pk)
            logger.info(f"🚀 Parseo async encolado para Boleto {boleto.pk}")

            return True

        except Exception as e:
            logger.exception(f"❌ Error crítico procesando email {msg_num}: {e}")
            return False

    def _procesar_boleto_pdf(self, message, msg_num, mail_connection):
        """Procesa todos los boletos desde PDFs adjuntos usando TicketParserService"""
        try:
            logger.info("📎 Investigando adjuntos PDF...")
            from django.apps import apps
            from django.core.files.base import ContentFile

            BoletoImportado = apps.get_model("bookings", "BoletoImportado")

            pdfs = self._extraer_adjuntos_pdf(message)
            if not pdfs:
                logger.error("No se encontraron PDFs adjuntos.")
                return False

            procesados_exito = 0
            for i, (filename, pdf_content) in enumerate(pdfs):
                logger.info(f"📄 Guardando PDF {i + 1}/{len(pdfs)}: {filename}")

                if not self._es_pdf_boleto_valido(pdf_content, filename):
                    logger.info(
                        f"⏭️ Omitiendo PDF '{filename}' por no parecer un boleto de avión válido."
                    )
                    continue

                final_filename = f"ticket_{msg_num}_{i}_{filename}"

                boleto = BoletoImportado(
                    agencia=self.agencia,
                    estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                    formato_detectado="PDF_AUTO",
                    log_parseo="",
                    numero_boleto="",
                    nombre_pasajero_completo="",
                    nombre_pasajero_procesado="",
                    localizador_pnr="",
                    ruta_vuelo="",
                    aerolinea_emisora="",
                    direccion_aerolinea="",
                    agente_emisor="",
                    foid_pasajero="",
                    impuestos_descripcion="",
                    telegram_file_id="",
                    raw_hash="",
                    datos_parseados={},
                )
                boleto.archivo_boleto.save(final_filename, ContentFile(pdf_content))
                boleto.save()
                logger.info(
                    f"📁 BoletoImportado ID {boleto.pk} guardado. Procesamiento en segundo plano iniciado por señal."
                )
                procesados_exito += 1

            return procesados_exito > 0

        except Exception as e:
            logger.exception(f"❌ Error crítico procesando PDFs {msg_num}: {e}")
            return False

    def _manejar_resultado_procesamiento(self, boleto, resultado):
        """Maneja la respuesta del Parser Service"""

        if isinstance(resultado, dict) and resultado.get("status") == "REVIEW_REQUIRED":
            logger.warning(f"⚠️ BOLETO {boleto.pk} REQUIERE REVISIÓN MANUAL (Datos faltantes)")

            msg = (
                f"⚠️ <b>ACCIÓN REQUERIDA</b>\n\n"
                f"Hemos recibido un boleto pero faltan datos (Cédula/ID).\n"
                f"🆔 Boleto ID: {boleto.pk}\n\n"
                f"👉 Por favor ingresa al Dashboard para completarlo."
            )

            from apps.communications.services.telegram_unified import send_telegram_alert_sync

            send_telegram_alert_sync(
                msg,
                token=self.agencia.telegram_bot_token,
                target_chat_id=self.agencia.telegram_chat_id,
            )

            return True

        if resultado:
            boleto.refresh_from_db()

            pdf_path = None
            if boleto.archivo_pdf_generado:
                pdf_path = boleto.archivo_pdf_generado.path

            logger.info(
                f"✅ Notificación centralizada manejada por el Servicio de Parseo para Boleto {boleto.pk}"
            )

            if pdf_path:
                self._enviar_respaldo_email(boleto, pdf_path)

            return True

        logger.error(f"❌ Procesamiento falló para Boleto {boleto.pk}")
        return False

    def _enviar_respaldo_email(self, boleto, pdf_path):
        """Envía copia oculta de respaldo a soporte de la agencia"""
        try:
            destino = getattr(self.agencia, "email_soporte", None)
            if not destino:
                return

            email_msg = EmailMessage(
                subject=f"Boleto Auto (Respaldo) - {boleto.localizador_pnr}",
                body=f"Respaldo automático ID {boleto.pk} para {self.agencia.nombre}",
                from_email=self.agencia.email_principal or settings.EMAIL_HOST_USER,
                to=[destino],
            )
            if pdf_path and os.path.exists(pdf_path):
                email_msg.attach_file(pdf_path)
            email_msg.send()
        except Exception as e:
            logger.warning(f"Error enviando respaldo email: {e}")

    def _enviar_notificacion(
        self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path, pdf_filename
    ):
        """Envía notificación usando el canal configurado"""

        if self.notification_type == "telegram":
            return self._enviar_telegram(
                sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path
            )

        elif self.notification_type == "whatsapp":
            return self._enviar_whatsapp(
                sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_filename
            )

        elif self.notification_type == "whatsapp_drive":
            return self._enviar_whatsapp_drive(
                sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path
            )

        elif self.notification_type == "email":
            return self._enviar_email(
                sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path
            )

        return False

    def _enviar_telegram(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
        """Envía notificación por Telegram con el PDF adjunto"""
        from apps.communications.services.telegram_unified import send_telegram_file_sync

        mensaje = (
            f"✈️ <b>Boleto {sistema} Procesado</b>\n\n"
            f"📍 PNR: <code>{localizador or 'N/A'}</code>\n"
            f"🎫 Boleto: {numero_boleto}\n"
            f"👤 Pasajero: {pasajero or 'N/A'}\n"
            f"✈️ Aerolínea: {aerolinea or 'N/A'}\n\n"
            f"<i>TravelHub - Oficina Digital</i>"
        )

        logger.info("📤 Enviando Telegram a Admin...")
        return send_telegram_file_sync(
            pdf_path,
            caption=mensaje,
            token=self.agencia.telegram_bot_token,
            target_chat_id=self.agencia.telegram_chat_id,
        )

    def _enviar_whatsapp(
        self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_filename
    ):
        """Envía notificación por WhatsApp"""
        from apps.communications.services.whatsapp_unified import enviar_whatsapp

        mensaje = f"""✈️ *Boleto {sistema} Procesado*

📍 PNR: *{localizador or "N/A"}*
🎫 Boleto: {numero_boleto}
👤 Pasajero: {pasajero or "N/A"}
✈️ Aerolínea: {aerolinea or "N/A"}
📄 PDF: {pdf_filename}

_TravelHub - Sistema Automático_"""

        return enviar_whatsapp(self.destination, mensaje)

    def _enviar_email(self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
        """Envía notificación por Email"""
        try:
            email_msg = EmailMessage(
                subject=f"Boleto {sistema} Procesado - {localizador}",
                body=f"""Boleto procesado automáticamente:

Sistema: {sistema}
PNR: {localizador}
Boleto: {numero_boleto}
Pasajero: {pasajero}
Aerolínea: {aerolinea}

PDF adjunto.

TravelHub - Sistema Automático""",
                to=[self.destination],
            )

            if self.agencia.email_principal:
                email_msg.from_email = self.agencia.email_principal

            email_msg.attach_file(pdf_path)
            email_msg.send()

            logger.info(f"✅ Email enviado: {numero_boleto}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
            return False

    def _enviar_whatsapp_drive(
        self, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path
    ):
        """Envía notificación por WhatsApp con link de Google Drive"""
        from apps.communications.services.whatsapp_unified import enviar_whatsapp

        drive_link = self._upload_to_drive(pdf_path)

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

        return enviar_whatsapp(self.destination, mensaje)

    def _upload_to_drive(self, pdf_path):
        """Sube PDF a Google Drive y retorna link público"""
        if not self.drive_service:
            return None

        try:
            file_metadata = {"name": os.path.basename(pdf_path), "mimeType": "application/pdf"}

            media = MediaFileUpload(pdf_path, mimetype="application/pdf")

            file = (
                self.drive_service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )

            file_id = file.get("id")

            self.drive_service.permissions().create(
                fileId=file_id, body={"type": "anyone", "role": "reader"}
            ).execute()

            return f"https://drive.google.com/uc?export=download&id={file_id}"
        except Exception as e:
            logger.error(f"❌ Error subiendo a Drive: {e}")
            return None

    def _tiene_pdf_adjunto(self, message):
        """Verifica si el mensaje tiene PDF adjunto"""
        if message.is_multipart():
            for part in message.walk():
                ctype = part.get_content_type()
                filename = part.get_filename() or ""

                logger.debug(f"Parte MIME: {ctype} - Filename: {filename}")

                if ctype == "application/pdf":
                    return True
                if filename.lower().endswith(".pdf"):
                    return True
        return False

    def _es_pdf_boleto_valido(self, pdf_content, filename=""):
        """
        Analiza el contenido en memoria de un PDF adjunto para determinar
        si es un boleto de avión legítimo o si es ruido.
        """
        if not PYPDF_AVAILABLE:
            logger.info("pypdf no está disponible. Omitiendo filtro anti-ruido.")
            return True

        try:
            import io

            reader = pypdf.PdfReader(io.BytesIO(pdf_content))

            # Limitar la lectura a las primeras 3 páginas para evitar PDFs gigantes
            max_pages = min(len(reader.pages), 3)
            texto = ""
            for idx in range(max_pages):
                try:
                    page_text = reader.pages[idx].extract_text()
                    if page_text:
                        texto += page_text + "\n"
                except Exception as page_err:
                    logger.debug(
                        f"Error extrayendo texto de página {idx} de {filename}: {page_err}"
                    )

            if not texto:
                # Si el PDF no tiene texto extraíble (por ejemplo, es escaneado/imagen),
                # permitimos por si acaso para no perder boletos legítimos escaneados.
                logger.info(
                    f"PDF {filename} no contiene texto extraíble. Podría ser una imagen o escaneo."
                )
                return True

            texto_upper = texto.upper()

            # Palabras clave fuertes (debe contener al menos una)
            palabras_clave_fuertes = [
                "PASSENGER",
                "PASAJERO",
                "ITINERARY",
                "ITINERARIO",
                "BOLETO",
                "TICKET",
                "BILLETE",
                "E-TICKET",
                "ETICKET",
            ]

            # Palabras clave de soporte/vuelo (debe contener al menos una si tiene fuerte, o 3 si no)
            palabras_clave_soporte = [
                "PNR",
                "LOCALIZADOR",
                "VUELO",
                "FLIGHT",
                "RESERVA",
                "RESERVACION",
                "CONFIRMACION",
                "CONFIRMED",
                "CONFIRMADO",
                "CLASE",
                "CLASS",
                "ASIENTO",
                "SEAT",
                "TARIFA",
                "FARE",
                "AEROLINEA",
                "AIRLINE",
                "SABRE",
                "KIU",
                "AMADEUS",
            ]

            tiene_fuerte = any(p in texto_upper for p in palabras_clave_fuertes)
            coincidencias_soporte = sum(1 for p in palabras_clave_soporte if p in texto_upper)

            # Regla: Debe tener al menos una fuerte y una de soporte, OR al menos tres de soporte
            es_valido = (tiene_fuerte and coincidencias_soporte >= 1) or (
                coincidencias_soporte >= 3
            )

            if not es_valido:
                logger.info(
                    f"🚫 PDF '{filename}' descartado por el filtro anti-ruido (Fuerte: {tiene_fuerte}, Soporte: {coincidencias_soporte})"
                )
                return False

            logger.info(
                f"✅ PDF '{filename}' pasó el filtro anti-ruido (Fuerte: {tiene_fuerte}, Soporte: {coincidencias_soporte})"
            )
            return True

        except Exception as e:
            logger.error(f"Error analizando PDF {filename} en filtro anti-ruido: {e}")
            # En caso de error, preferimos falsos positivos a falsos negativos (dejar pasar el PDF)
            return True

    def _extraer_adjuntos_pdf(self, message):
        """Extrae el contenido de todos los PDF adjuntos"""
        from email.header import decode_header

        pdfs = []
        if message.is_multipart():
            for part in message.walk():
                ctype = part.get_content_type()
                raw_filename = part.get_filename()
                filename = None

                if raw_filename:
                    try:
                        decoded_parts = decode_header(raw_filename)
                        filename_parts = []
                        for val, encoding in decoded_parts:
                            if isinstance(val, bytes):
                                filename_parts.append(
                                    val.decode(encoding or "utf-8", errors="ignore")
                                )
                            else:
                                filename_parts.append(val)
                        filename = "".join(filename_parts)
                    except Exception:
                        filename = raw_filename

                is_pdf = (ctype == "application/pdf") or (
                    filename and filename.lower().endswith(".pdf")
                )

                if is_pdf:
                    if not filename:
                        filename = "adjunto.pdf"
                    payload = part.get_payload(decode=True)
                    if payload:
                        pdfs.append((filename, payload))
        return pdfs

    def _extraer_pdf(self, message):
        """Extrae el contenido del primer PDF adjunto (Retrocompatibilidad)"""
        pdfs = self._extraer_adjuntos_pdf(message)
        return pdfs[0][1] if pdfs else None

    def _extraer_texto(self, message):
        """Extrae texto plano del email"""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            return message.get_payload(decode=True).decode("utf-8", errors="ignore")
        return None

    def _extraer_html(self, message):
        """Extrae HTML del email"""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            content = message.get_payload(decode=True).decode("utf-8", errors="ignore")
            if "<HTML>" in content.upper():
                return content
        return None

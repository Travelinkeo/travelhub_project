import email
import imaplib
import logging
from email.header import decode_header

from django.conf import settings

logger = logging.getLogger(__name__)


class EmailIngestionService:
    """
    Servicio para la ingesta de correos electrónicos vía IMAP.
    Primer paso del pipeline Mail-to-TKT.
    """

    def __init__(self, host=None, user=None, password=None, port=993):
        self.host = host or getattr(settings, "IMAP_HOST", "imap.gmail.com")
        self.user = user or getattr(settings, "IMAP_USER", "")
        self.password = password or getattr(settings, "IMAP_PASSWORD", "")
        self.port = port
        self.imap = None

    def _connect(self):
        """Establece conexión con el servidor IMAP."""
        try:
            if not self.host or not self.user or not self.password:
                logger.error("Configuración IMAP incompleta.")
                return False

            self.imap = imaplib.IMAP4_SSL(self.host, self.port)
            self.imap.login(self.user, self.password)
            return True
        except Exception as e:
            logger.error(f"Error de conexión IMAP a {self.host}: {e}")
            return False

    def fetch_unread_emails(self):
        """
        Busca correos no leídos, extrae contenido y los marca como leídos.
        Retorna una lista de diccionarios estructurados.
        """
        if not self._connect():
            return []

        processed_emails = []
        try:
            # Seleccionar bandeja de entrada
            self.imap.select("INBOX")

            # Buscar correos no leídos (UNSEEN)
            status, messages = self.imap.search(None, "UNSEEN")

            if status != "OK":
                logger.warning(f"No se pudieron buscar correos UNSEEN para {self.user}")
                return []

            email_ids = messages[0].split()
            logger.info(
                f"📬 [IMAP] Se encontraron {len(email_ids)} correos no leídos en {self.user}"
            )

            for e_id in email_ids:
                # Fetch del contenido del correo
                status, msg_data = self.imap.fetch(e_id, "(RFC822)")
                if status != "OK":
                    logger.error(f"Error al obtener correo ID {e_id}")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        # Parsear bytes a objeto mensaje
                        msg = email.message_from_bytes(response_part[1])

                        # Extraer y decodificar Asunto
                        subject, encoding = decode_header(msg.get("Subject", "Sin Asunto"))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(
                                encoding if encoding else "utf-8", errors="replace"
                            )

                        # Remitente
                        from_ = msg.get("From")

                        # Extraer Cuerpo (Priorizar texto plano, fallback a HTML)
                        body = self._extract_body(msg)

                        # Extraer Adjuntos
                        attachments = self._extract_attachments(msg)

                        processed_emails.append(
                            {
                                "uid": e_id.decode(),
                                "subject": subject,
                                "from": from_,
                                "body": body,
                                "date": msg.get("Date"),
                                "attachments": attachments,
                                "is_invoice": self._is_invoice_email(subject, attachments),
                            }
                        )

                        # Marcar como leído
                        self.imap.store(e_id, "+FLAGS", "\\Seen")

            return processed_emails

        except Exception as e:
            logger.error(f"Error crítico en fetch_unread_emails: {e}")
            return []
        finally:
            if self.imap:
                try:
                    self.imap.close()
                    self.imap.logout()
                except Exception:
                    logger.debug("IMAP cleanup error (non-critical)", exc_info=True)

    def _extract_attachments(self, msg):
        """Extrae los adjuntos del correo."""
        attachments = []
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue

            filename = part.get_filename()
            if filename:
                # Decodificar el nombre del archivo
                decoded_filename, encoding = decode_header(filename)[0]
                if isinstance(decoded_filename, bytes):
                    filename = decoded_filename.decode(encoding or "utf-8", errors="replace")

                import base64

                attachments.append(
                    {
                        "filename": filename,
                        "content_type": part.get_content_type(),
                        "content": base64.b64encode(part.get_payload(decode=True)).decode("utf-8"),
                    }
                )
        return attachments

    def _is_invoice_email(self, subject, attachments):
        """Detecta si el correo parece ser una factura de proveedor."""
        keywords = ["factura", "invoice", "liquidación", "settlement", "nota de débito", "billing"]
        subject_lower = subject.lower()

        has_keyword = any(kw in subject_lower for kw in keywords)
        has_pdf = any(att["content_type"] == "application/pdf" for att in attachments)

        return has_keyword and has_pdf

    def _extract_body(self, msg):
        """Extrae el contenido de texto del mensaje, limpiando HTML si es necesario."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="replace")
                        break
                elif content_type == "text/html" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_content = payload.decode(errors="replace")
                        body = self._clean_html(html_content)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="replace")
                if msg.get_content_type() == "text/html":
                    body = self._clean_html(body)

        return body.strip()

    def _clean_html(self, html):
        """Limpia el HTML para obtener texto legible."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            # Eliminar scripts y estilos
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            return soup.get_text(separator=" ")
        except ImportError:
            # Fallback si bs4 no está
            import re

            return re.sub("<[^<]+?>", "", html)

    @classmethod
    def from_agency(cls, agencia):
        """
        Factory method para instanciar el servicio desde la configuración de una agencia.
        """
        config = agencia.configuracion
        return cls(
            host=config.email_monitor_host,
            user=config.email_monitor_user,
            password=config.email_monitor_password,
            port=config.email_monitor_port,
        )

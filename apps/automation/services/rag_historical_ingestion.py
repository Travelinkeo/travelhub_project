import email
import imaplib
import logging
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime

from django.apps import apps
from django.utils import timezone

from apps.automation.services.rag_service import RAGKnowledgeService
from core.models import Agencia

logger = logging.getLogger(__name__)


class RAGHistoricalEmailIngestionService:
    """
    Servicio para la extracción, filtrado inteligente y vectorización histórica de correos
    (ej. travelinkeo@gmail.com) acumulados desde 2013.
    """

    @classmethod
    def _get_log_model(cls):
        """Retorna dinámicamente el modelo KBHistoricalEmailLog."""
        return apps.get_model("cms", "KBHistoricalEmailLog")

    @classmethod
    def _decode_str(cls, header_val: str) -> str:
        """Decodifica encabezados de correo MIME a utf-8."""
        if not header_val:
            return ""
        decoded_fragments = decode_header(header_val)
        result = []
        for fragment, encoding in decoded_fragments:
            if isinstance(fragment, bytes):
                try:
                    result.append(fragment.decode(encoding or "utf-8", errors="ignore"))
                except Exception:
                    result.append(fragment.decode("latin-1", errors="ignore"))
            else:
                result.append(str(fragment))
        return "".join(result)

    @classmethod
    def is_ticket_or_fly_notification(cls, subject: str, sender: str, body: str) -> bool:
        """
        Descarta correos transaccionales directos de boletos ya procesados (e-tickets)
        y conserva SOLO boletines, comunicaciones, cambios de comisión o tarifarios de aerolíneas.
        """
        combined = f"{subject} {body[:500]}".upper()

        # Palabras de descarte (Boletos de pasajeros individuales que saturan el RAG)
        discard_patterns = [
            r"ITINERARY RECEIPT",
            r"ELECTRONIC TICKET RECEIPT",
            r"BOLETO ELECTRONICO",
            r"RECIBO DE PASAJE",
            r"CONFIRMACION DE RESERVA",
            r"PASAJERO:",
            r"CHECK-IN CONFIRMED",
            r"TARJETA DE EMBARQUE",
            r"BOARDING PASS",
            r"TU VUELO ESTA CERCA",
        ]

        for pattern in discard_patterns:
            if re.search(pattern, combined):
                return False

        # Palabras de inclusión (Comunicaciones oficiales de valor RAG)
        keep_patterns = [
            r"COMUNICADO",
            r"NOTIFICACION",
            r"CIRCULAR",
            r"POLITICA",
            r"INFORMATIVO",
            r"EQUIPAJE",
            r"COMISION",
            r"TARIFARIO",
            r"PROMOCION",
            r"REGULACION",
            r"AVISO IMPORTANTE",
            r"REGLA DE TARIFA",
            r"PENALIDAD",
            r"VENEZUELA",
            r"SABRE",
            r"AMADEUS",
            r"KIU",
            r"LASER",
            r"AVIOR",
            r"RUTACA",
            r"ESTELAR",
            r"CONVIASA",
            r"COPA",
            r"TURKISH",
        ]

        for pattern in keep_patterns:
            if re.search(pattern, combined):
                return True

        return False

    @classmethod
    def ingest_imap_folder(
        cls,
        agencia: Agencia,
        email_user: str,
        email_password: str,
        imap_server: str = "imap.gmail.com",
        folder: str = "INBOX",
        limit: int = 200,
    ) -> dict[str, int]:
        """
        Se conecta por IMAP, escanea correos históricos, filtra ruido y los vectoriza en el RAG.
        """
        KBHistoricalEmailLog = cls._get_log_model()
        stats = {
            "total_found": 0,
            "processed_and_indexed": 0,
            "skipped_existing": 0,
            "skipped_irrelevant": 0,
            "errors": 0,
        }

        try:
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_user, email_password)
            status, _ = mail.select(folder, readonly=True)

            if status != "OK":
                logger.error(f"RAG: No se pudo seleccionar la carpeta IMAP {folder}")
                return stats

            # Buscar todos los correos
            status, data = mail.search(None, "ALL")
            if status != "OK" or not data[0]:
                logger.info(f"RAG: No se encontraron correos en {folder} para {email_user}.")
                mail.logout()
                return stats

            email_ids = data[0].split()
            stats["total_found"] = len(email_ids)
            logger.info(f"Se encontraron {len(email_ids)} correos en {folder} para {email_user}.")

            # Procesar correos desde los más recientes hacia atrás
            email_ids = list(reversed(email_ids))[:limit]

            for e_id in email_ids:
                uid_str = f"{email_user}_{e_id.decode()}"

                # Verificar si ya fue procesado previamente
                if KBHistoricalEmailLog.objects.filter(
                    message_id=uid_str, agencia=agencia
                ).exists():
                    stats["skipped_existing"] += 1
                    continue

                res, msg_data = mail.fetch(e_id, "(RFC822)")
                if res != "OK" or not msg_data:
                    stats["errors"] += 1
                    continue

                raw_email = None
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        raw_email = response_part[1]
                        break

                if not raw_email:
                    stats["errors"] += 1
                    continue

                msg = email.message_from_bytes(raw_email)
                subject = cls._decode_str(msg.get("Subject", ""))
                sender = cls._decode_str(msg.get("From", ""))

                date_sent = None
                date_header = msg.get("Date")
                if date_header:
                    try:
                        date_sent = parsedate_to_datetime(date_header)
                    except Exception as e_dt:
                        logger.debug("Error convirtiendo fecha de correo: %s", e_dt)
                        date_sent = timezone.now()

                # Extraer cuerpo (texto plano preferido)
                body = ""
                pdf_attachments = []

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))

                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            try:
                                body += part.get_payload(decode=True).decode(
                                    part.get_content_charset() or "utf-8", errors="ignore"
                                )
                            except Exception as e_dec:
                                logger.debug("Error decodificando texto plano: %s", e_dec)
                        elif (
                            content_type == "text/html"
                            and not body
                            and "attachment" not in content_disposition
                        ):
                            try:
                                html_payload = part.get_payload(decode=True).decode(
                                    part.get_content_charset() or "utf-8", errors="ignore"
                                )
                                # Limpiar etiquetas HTML simples
                                body = re.sub(r"<[^>]+>", " ", html_payload)
                            except Exception as e_html:
                                logger.debug("Error decodificando HTML: %s", e_html)
                        elif "attachment" in content_disposition and part.get_filename():
                            fname = cls._decode_str(part.get_filename())
                            if fname.lower().endswith(".pdf"):
                                try:
                                    pdf_attachments.append((fname, part.get_payload(decode=True)))
                                except Exception as e_att:
                                    logger.debug("Error obteniendo adjunto PDF: %s", e_att)
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(
                            msg.get_content_charset() or "utf-8", errors="ignore"
                        )
                    except Exception as e_raw:
                        logger.debug("Error decodificando payload raw: %s", e_raw)

                # Filtrar si es relevante para la Base de Conocimientos RAG
                is_relevant = cls.is_ticket_or_fly_notification(subject, sender, body)
                if not is_relevant:
                    stats["skipped_irrelevant"] += 1
                    KBHistoricalEmailLog.objects.create(
                        agencia=agencia,
                        message_id=uid_str,
                        subject=subject[:255],
                        sender=sender[:255],
                        date_sent=date_sent,
                        status="SKIPPED",
                        chunks_created=0,
                        reason="Omitido por filtro de irrelevancia/boleto pasajero",
                    )
                    continue

                # Vectorizar en la base de datos de RAG Knowledge
                chunks_count = RAGKnowledgeService.index_email_content(
                    subject=subject, body=body, source_email=sender, agencia=agencia
                )

                KBHistoricalEmailLog.objects.create(
                    agencia=agencia,
                    message_id=uid_str,
                    subject=subject[:255],
                    sender=sender[:255],
                    date_sent=date_sent,
                    status="INDEXED" if chunks_count > 0 else "SKIPPED",
                    chunks_created=chunks_count,
                    reason=f"Indexado exitosamente ({chunks_count} chunks)",
                )

                stats["processed_and_indexed"] += 1

            mail.logout()
        except Exception as e:
            logger.error(f"RAG: Error en ingesta histórica IMAP para {email_user}: {e}")
            stats["errors"] += 1

        return stats

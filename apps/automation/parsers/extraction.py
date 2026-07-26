import logging
import os
from email import policy
from email.parser import BytesParser
from typing import Any, BinaryIO

try:
    import fitz
except ImportError:
    fitz = None

try:
    from bs4 import BeautifulSoup, NavigableString
except ImportError:
    BeautifulSoup = None
    NavigableString = None


logger = logging.getLogger(__name__)


class ExtractionService:
    """
    🎯 Responsabilidad: Convertir archivos binarios (PDF, EML, TXT) en texto plano.
    """

    @staticmethod
    def extract_text(file_obj: BinaryIO, filename: str) -> str | None:
        """Extract plain text from a PDF, EML or any binary file.

        Returns the extracted text or ``None`` on error.
        """
        try:
            filename = filename.lower()
            if filename.endswith(".pdf"):
                return ExtractionService._extract_pdf(file_obj)
            elif filename.endswith(".eml"):
                return ExtractionService._extract_eml(file_obj)
            else:
                content = file_obj.read()
                if isinstance(content, bytes | bytearray):
                    return content.decode("utf-8", errors="ignore")
                return str(content)
        except Exception as e:
            logger.error(f"Error extrayendo texto de archivo {filename}: {e}")
            return None

    @staticmethod
    def _extract_pdf(file_obj):
        if fitz is None:
            logger.error("PyMuPDF (fitz) no está instalado. No se puede extraer texto de PDF.")
            return None
        texto_extraido = ""
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            file_content = file_obj.read()
            with fitz.open(stream=file_content, filetype="pdf") as pdf:
                for page in pdf:
                    try:
                        text = page.get_text()
                        if text:
                            texto_extraido += text + "\n"
                    except Exception as e:
                        logger.warning(f"Error extrayendo página de PDF: {e}")
                        continue
        except Exception as e:
            logger.error(f"Fallo PyMuPDF: {e}")

        return texto_extraido

    @staticmethod
    def _extract_eml(file_obj):
        msg = BytesParser(policy=policy.default).parse(file_obj)
        texto_final = "--- HEADERS START ---\n"
        essential_headers = ["Subject", "From", "To", "Date"]

        if hasattr(msg, "items"):
            for k, v in msg.items():
                if k in essential_headers:
                    texto_final += f"{k}: {v}\n"
        texto_final += "--- HEADERS END ---\n\n"

        html_found = False
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                filename = part.get_filename()
                if filename:
                    try:
                        from email.header import decode_header

                        decoded, encoding = decode_header(filename)[0]
                        if isinstance(decoded, bytes):
                            filename = decoded.decode(encoding or "utf-8", errors="replace")
                    except Exception as e:
                        logger.debug("Ignored exception decoding email header: %s", e)
                    filename_lower = filename.lower()
                    if filename_lower.endswith(".pdf"):
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                import io

                                pdf_text = ExtractionService._extract_pdf(io.BytesIO(payload))
                                if pdf_text:
                                    texto_final += (
                                        f"\n\n--- ATTACHMENT PDF: {filename} ---\n{pdf_text}\n"
                                    )
                        except Exception as e_pdf:
                            logger.warning(f"Error extrayendo PDF adjunto {filename}: {e_pdf}")
                    elif filename_lower.endswith(".txt"):
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or "utf-8"
                                txt_text = payload.decode(charset, errors="replace")
                                texto_final += (
                                    f"\n\n--- ATTACHMENT TXT: {filename} ---\n{txt_text}\n"
                                )
                        except Exception as e_txt:
                            logger.warning(f"Error extrayendo TXT adjunto {filename}: {e_txt}")
                    # Skip normal body parsing for non-inline attachment parts
                    continue

                try:
                    if ctype == "text/html":
                        payload = part.get_payload(decode=True)
                        if not payload:
                            continue
                        charset = part.get_content_charset() or "utf-8"
                        if isinstance(payload, bytes | bytearray):
                            content = payload.decode(charset, errors="replace")
                        else:
                            content = str(payload)
                        texto_final += ExtractionService._clean_html(content)
                        html_found = True
                    elif ctype == "text/plain" and not html_found:
                        payload = part.get_payload(decode=True)
                        if not payload:
                            continue
                        charset = part.get_content_charset() or "utf-8"
                        if isinstance(payload, bytes | bytearray):
                            content = payload.decode(charset, errors="replace")
                        else:
                            content = str(payload)
                        texto_final += content
                except Exception as e:
                    logger.warning(f"Error procesando parte MIME del EML: {e}")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                content = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    texto_final += ExtractionService._clean_html(content)
                else:
                    texto_final += content
        return texto_final

    @staticmethod
    def extract_html(file_obj: BinaryIO, filename: str) -> str:
        """Extract raw HTML content from a file (EML or HTML).

        Unlike ``extract_text``, this preserves the original HTML structure
        so that parsers can navigate the DOM with BeautifulSoup.
        """
        try:
            filename = filename.lower()
            if not filename.endswith(".eml") and not filename.endswith(".html"):
                return ""
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            msg = BytesParser(policy=policy.default).parse(file_obj)
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            if isinstance(payload, bytes | bytearray):
                                return payload.decode(charset, errors="replace")
                            return str(payload)
            else:
                payload = msg.get_payload(decode=True)
                if payload and msg.get_content_type() == "text/html":
                    charset = msg.get_content_charset() or "utf-8"
                    if isinstance(payload, bytes | bytearray):
                        return payload.decode(charset, errors="replace")
                    return str(payload)
            return ""
        except Exception as e:
            logger.error(f"Error extrayendo HTML de archivo {filename}: {e}")
            return ""

    @staticmethod
    def _clean_html(html_content: str) -> str:
        if BeautifulSoup is None:
            return html_content
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for s in soup(["script", "style", "head", "title", "meta"]):
                s.decompose()

            # Replace br and hr with newlines
            for br in soup.find_all(["br", "hr"]):
                # Use NavigableString to satisfy mypy type expectations
                br.replace_with(NavigableString("\n"))

            # Insert newlines around block elements to maintain block structure
            block_elements = [
                "p",
                "div",
                "tr",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "li",
                "ul",
                "ol",
                "table",
            ]
            for element in soup.find_all(block_elements):
                element.insert_before("\n")
                element.insert_after("\n")

            text = soup.get_text(separator="")
            return "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        except Exception:
            return html_content

    @staticmethod
    def get_open_file(boleto: Any) -> BinaryIO | None:
        """Obtener un handle de lectura binaria para el archivo del boleto.

        Soporta almacenamiento local y remoto (Cloudflare R2/S3) de forma transparente.
        """
        if not boleto.archivo_boleto:
            return None
        try:
            # Django S3Boto3Storage maneja la apertura remota automáticamente
            f = boleto.archivo_boleto.open("rb")
            f.seek(0)
            return f
        except Exception as e:
            logger.error(f"❌ Error crítico abriendo archivo de boleto {boleto.pk}: {e}")
            # Si falla el storage, intentamos un fallback desesperado si es local
            try:
                if hasattr(boleto.archivo_boleto, "path") and os.path.exists(
                    boleto.archivo_boleto.path
                ):
                    return open(boleto.archivo_boleto.path, "rb")
            except (OSError, ValueError):
                logger.debug("Could not open boleto file: %s", boleto.archivo_boleto, exc_info=True)
            return None

import io
import logging
from email import policy
from email.parser import BytesParser

import fitz
import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


logger = logging.getLogger(__name__)

class ExtractionService:
    """
    🎯 Responsabilidad: Convertir archivos binarios (PDF, EML, TXT) en texto plano.
    """
    
    @staticmethod
    def extract_text(file_obj, filename):
        try:
            filename = filename.lower()
            if filename.endswith('.pdf'):
                return ExtractionService._extract_pdf(file_obj)
            elif filename.endswith('.eml'):
                return ExtractionService._extract_eml(file_obj)
            else:
                content = file_obj.read()
                return content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error extrayendo texto de archivo {filename}: {e}")
            return None

    @staticmethod
    def _extract_pdf(file_obj):
        texto_extraido = ""
        try:
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            file_content = file_obj.read()
            with fitz.open(stream=file_content, filetype="pdf") as pdf:
                for page in pdf:
                    try:
                        text = page.get_text()
                        if text: texto_extraido += text + "\n"
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
        essential_headers = ['Subject', 'From', 'To', 'Date']
        
        if hasattr(msg, 'items'):
            for k, v in msg.items():
                if k in essential_headers:
                    texto_final += f"{k}: {v}\n"
        texto_final += "--- HEADERS END ---\n\n"
        
        html_found = False
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                try:
                    if ctype == 'text/html':
                        payload = part.get_payload(decode=True)
                        if not payload: continue
                        charset = part.get_content_charset() or 'utf-8'
                        content = payload.decode(charset, errors='replace')
                        texto_final += ExtractionService._clean_html(content)
                        html_found = True
                    elif ctype == 'text/plain' and not html_found:
                        payload = part.get_payload(decode=True)
                        if not payload: continue
                        charset = part.get_content_charset() or 'utf-8'
                        content = payload.decode(charset, errors='replace')
                        texto_final += content
                except Exception as e:
                    logger.warning(f"Error procesando parte MIME del EML: {e}")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                content = payload.decode(charset, errors='replace')
                if msg.get_content_type() == 'text/html':
                    texto_final += ExtractionService._clean_html(content)
                else:
                    texto_final += content
        return texto_final

    @staticmethod
    def _clean_html(html_content):
        if not BeautifulSoup: return html_content
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for s in soup(["script", "style", "head", "title", "meta"]):
                s.decompose()
            
            # Replace br and hr with newlines
            for br in soup.find_all(["br", "hr"]):
                br.replace_with("\n")
                
            # Insert newlines around block elements to maintain block structure
            block_elements = ["p", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "table"]
            for element in soup.find_all(block_elements):
                element.insert_before("\n")
                element.insert_after("\n")
                
            text = soup.get_text(separator='')
            return '\n'.join([l.strip() for l in text.splitlines() if l.strip()])
        except Exception as e:
            return html_content

    @staticmethod
    def get_open_file(boleto):
        """
        🎯 Responsabilidad: Obtener un handle de lectura binaria para el archivo del boleto.
        Soporta almacenamiento local y remoto (Cloudflare R2/S3) de forma transparente.
        """
        try:
            # Django S3Boto3Storage maneja la apertura remota automáticamente
            # sin necesidad de requests manuales, lo cual es más seguro y eficiente.
            f = boleto.archivo_boleto.open('rb')
            f.seek(0)
            return f
        except Exception as e:
            logger.error(f"❌ Error crítico abriendo archivo de boleto {boleto.pk}: {e}")
            # Si falla el storage, intentamos un fallback desesperado si es local
            try:
                if hasattr(boleto.archivo_boleto, 'path') and os.path.exists(boleto.archivo_boleto.path):
                    return open(boleto.archivo_boleto.path, 'rb')
            except:
                pass
            return None

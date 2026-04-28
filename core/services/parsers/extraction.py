# -*- coding: utf-8 -*-
import logging
import io
import requests
import pdfplumber
from email import policy
from email.parser import BytesParser
from io import BytesIO

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

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
            with pdfplumber.open(file_obj) as pdf:
                for page in pdf.pages:
                    try:
                        text = page.extract_text()
                        if text: texto_extraido += text + "\n"
                    except Exception as e:
                        logger.warning(f"Error extrayendo página de PDF: {e}")
                        continue
        except Exception as e:
            logger.error(f"Fallo pdfplumber: {e}")

        # Fallback a pypdf/PyPDF2
        texto_fallback = ""
        try:
            file_obj.seek(0)
            reader = None
            if pypdf: reader = pypdf.PdfReader(file_obj)
            elif PyPDF2: reader = PyPDF2.PdfReader(file_obj)
            
            if reader:
                for page in reader.pages:
                    texto_fallback += (page.extract_text() or "") + "\n"
                if texto_fallback:
                    texto_extraido += "\n\n--- FALLBACK EXTRACTION ---\n\n" + texto_fallback
        except Exception as e:
            logger.warning(f"Fallback PDF extraction falló: {e}")
        
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
                except: pass
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
            text = soup.get_text(separator='\n')
            return '\n'.join([l.strip() for l in text.splitlines() if l.strip()])
        except:
            return html_content

    @staticmethod
    def get_open_file(boleto):
        """Descarga o abre el archivo del boleto."""
        if hasattr(boleto.archivo_boleto, 'url') and boleto.archivo_boleto.url.startswith('http'):
            try:
                response = requests.get(boleto.archivo_boleto.url, timeout=15)
                response.raise_for_status()
                return BytesIO(response.content)
            except Exception as e:
                logger.error(f"Error descargar boleto remoto: {e}")
        
        f = boleto.archivo_boleto.open('rb')
        f.seek(0)
        return f

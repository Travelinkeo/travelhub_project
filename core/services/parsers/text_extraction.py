import logging
import pdfplumber
import tempfile
import os
import email
from email import policy
from typing import Optional

logger = logging.getLogger(__name__)

class TextExtractionService:
    """
    Microservicio dedicado exclusivamente a extraer texto crudo de archivos físicos.
    Responsabilidad Única: I/O de archivos.
    """
    
    @staticmethod
    def extract_from_file(file_obj, filename: str) -> str:
        """Dispatcher principal basado en la extensión o tipo MIME."""
        filename = filename.lower()
        
        try:
            if filename.endswith('.pdf'):
                return TextExtractionService.extract_from_pdf(file_obj)
            elif filename.endswith('.eml'):
                return TextExtractionService.extract_from_eml(file_obj)
            else:
                return file_obj.read().decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error extrayendo texto del archivo {filename}: {e}")
            return ""

    @staticmethod
    def extract_from_pdf(file_obj) -> str:
        """Extracción centralizada de PDFs usando pdfplumber."""
        texto_extraido = ""
        try:
            # Aseguramos puntero al inicio
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            with pdfplumber.open(file_obj) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texto_extraido += text + "\n"
        except Exception as e:
            logger.error(f"Fallo al leer PDF: {e}")
        return texto_extraido

    @staticmethod
    def extract_from_eml(file_obj) -> str:
        """Lectura de correos electrónicos y búsqueda de PDFs adjuntos."""
        texto_extraido = ""
        try:
            # Si file_obj es un archivo de Django, leemos su contenido binario
            file_content = file_obj.read() if hasattr(file_obj, 'read') else file_obj
            if isinstance(file_content, str):
                file_content = file_content.encode('utf-8')
                
            msg = email.message_from_bytes(file_content, policy=policy.default)
            
            # 1. Extraer el cuerpo del correo
            body = msg.get_body(preferencelist=('plain', 'html'))
            if body:
                texto_extraido += body.get_content() + "\n"
                
            # 2. Buscar PDFs adjuntos (Híbrido)
            for part in msg.walk():
                if part.get_content_type() == 'application/pdf':
                    pdf_payload = part.get_payload(decode=True)
                    if pdf_payload:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                            tmp_pdf.write(pdf_payload)
                            tmp_pdf_path = tmp_pdf.name
                        
                        logger.info("📄 PDF adjunto encontrado en el EML. Extrayendo...")
                        with open(tmp_pdf_path, 'rb') as f_pdf:
                            texto_extraido += "\n--- TEXTO ADJUNTO PDF ---\n"
                            texto_extraido += TextExtractionService.extract_from_pdf(f_pdf)
                            
                        try:
                            os.unlink(tmp_pdf_path)
                        except:
                            pass
        except Exception as e:
            logger.error(f"Fallo al leer EML: {e}")
            
        return texto_extraido

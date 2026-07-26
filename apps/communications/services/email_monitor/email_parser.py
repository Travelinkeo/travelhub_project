import logging

logger = logging.getLogger(__name__)

PYPDF_AVAILABLE = True


def extraer_texto_plano(message):
    """extraer_texto_plano."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="ignore")
    else:
        return message.get_payload(decode=True).decode("utf-8", errors="ignore")
    return None


def extraer_html(message):
    """extraer_html."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode("utf-8", errors="ignore")
    else:
        content = message.get_payload(decode=True).decode("utf-8", errors="ignore")
        if "<HTML>" in content.upper():
            return content
    return None


def extraer_adjuntos_pdf(message):
    """extraer_adjuntos_pdf."""
    pdfs = []
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            filename = part.get_filename() or "adjunto.pdf"
            is_pdf = (ctype == "application/pdf") or (filename.lower().endswith(".pdf"))
            if is_pdf:
                payload = part.get_payload(decode=True)
                if payload:
                    pdfs.append((filename, payload))
    return pdfs


def extraer_primer_pdf(message):
    """extraer_primer_pdf."""
    pdfs = extraer_adjuntos_pdf(message)
    return pdfs[0][1] if pdfs else None


def tiene_pdf_adjunto(message):
    """tiene_pdf_adjunto."""
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            filename = part.get_filename() or ""
            if ctype == "application/pdf":
                return True
            if filename.lower().endswith(".pdf"):
                return True
    return False

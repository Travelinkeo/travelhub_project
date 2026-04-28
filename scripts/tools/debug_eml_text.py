
import os
import sys
import logging
import io
from bs4 import BeautifulSoup

# Configurar logging mínimo
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simular la lógica de TicketParserService.extraer_texto_desde_archivo para EML
def simulate_eml_extraction(file_path):
    from email import policy
    from email.parser import BytesParser
    
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    
    texto_final = "--- HEADERS START ---\n"
    essential_headers = ['Subject', 'From', 'To', 'Date']
    for k, v in msg.items():
        if k in essential_headers:
            texto_final += f"{k}: {v}\n"
    texto_final += "--- HEADERS END ---\n\n"
    
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == 'text/html':
                payload = part.get_payload(decode=True)
                if not payload: continue
                charset = part.get_content_charset() or 'utf-8'
                content = payload.decode(charset, errors='replace')
                
                soup = BeautifulSoup(content, 'html.parser')
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                text_clean = soup.get_text(separator='\n')
                
                # Limpiar líneas vacías excesivas
                lines = [l.strip() for l in text_clean.splitlines() if l.strip()]
                texto_final += "\n".join(lines)
                break # Solo procesamos el primer HTML
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or 'utf-8'
        texto_final += payload.decode(charset, errors='replace')
        
    return texto_final

if __name__ == "__main__":
    eml_path = r"C:\Users\ARMANDO\Downloads\Tickets Avior Airlines.eml"
    if os.path.exists(eml_path):
        text = simulate_eml_extraction(eml_path)
        print("--- EXTRACTED TEXT (PREVIEW) ---")
        print(text[:2000])
        print("--- END PREVIEW ---")
        
        # Guardar en un temporal para analizarlo completo
        with open("extracted_eml_debug.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nTexto completo guardado en: {os.path.abspath('extracted_eml_debug.txt')}")
    else:
        print(f"File not found: {eml_path}")

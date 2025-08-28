import os, sys, json, email
from email import policy
from bs4 import BeautifulSoup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from external_ticket_generator.KIU.mi_proyecto_final.mi_proyecto_final.main import extract_data_from_text

KIU_DIR = os.path.join(ROOT, 'external_ticket_generator', 'KIU')

def load_eml(path: str):
    with open(path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    html_body = ''
    plain_text = ''
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get('Content-Disposition'))
            if 'attachment' in cdisp:
                continue
            charset = part.get_content_charset() or 'utf-8'
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            try:
                decoded = payload.decode(charset, errors='ignore')
            except Exception:
                decoded = payload.decode('utf-8', errors='ignore')
            if ctype == 'text/html':
                html_body = decoded
            elif ctype == 'text/plain':
                plain_text = decoded
    else:
        charset = msg.get_content_charset() or 'utf-8'
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(charset, errors='ignore')
            if msg.get_content_type() == 'text/html':
                html_body = decoded
            else:
                plain_text = decoded
    if not plain_text and html_body:
        plain_text = BeautifulSoup(html_body, 'html.parser').get_text('\n')
    return plain_text, html_body

def main():
    print("=== Parseo masivo de EML KIU ===")
    eml_files = [f for f in os.listdir(KIU_DIR) if f.lower().endswith('.eml')]
    eml_files.sort()
    resultados = []
    for fname in eml_files:
        path = os.path.join(KIU_DIR, fname)
        try:
            plain_text, html_text = load_eml(path)
            if not plain_text.strip():
                print(f"[SKIP] {fname}: sin texto plano usable")
                continue
            data = extract_data_from_text(plain_text, html_text)
            resultados.append({
                'file': fname,
                'passenger': data.get('NOMBRE_DEL_PASAJERO'),
                'solo_nombre': data.get('SOLO_NOMBRE_PASAJERO'),
                'ticket': data.get('NUMERO_DE_BOLETO'),
            })
            print(f"[OK] {fname} -> {data.get('NOMBRE_DEL_PASAJERO')} | Solo: {data.get('SOLO_NOMBRE_PASAJERO')}")
        except Exception as e:
            print(f"[ERR] {fname}: {e}")
    # Resumen de valores sospechosos (contienen CIUDAD / PANAMA / COLOMBIA al final)
    sospechosos = [r for r in resultados if r['passenger'] and re.search(r'( CIUDAD| PANAMA| COLOMBIA)$', r['passenger'])]
    print("\nResumen:")
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
    if sospechosos:
        print("\nATENCIÓN: Encontrados posibles nombres contaminados:")
        for s in sospechosos:
            print(" -", s['file'], "=>", s['passenger'])
    else:
        print("\nNo se detectaron nombres con sufijos de ubicación residuales.")

if __name__ == '__main__':
    import re
    main()

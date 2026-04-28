
#!/usr/bin/env python3
"""Genera y envía los 3 documentos estratégicos de TravelHub como un PDF unificado."""
import os, smtplib, markdown
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

BASE  = r"C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d"
DOCS  = [
    (f"{BASE}\\Analisis_Estrategico_TravelHub.md",   "Análisis Estratégico"),
    (f"{BASE}\\Plan_Complementario_v2_TravelHub.md", "Plan Complementario v2"),
    (f"{BASE}\\PMV_Sprint_Guerra_TravelHub.md",       "PMV + Sprint de Guerra"),
]
PDF_OUT = f"{BASE}\\TravelHub_Plan_Completo_2026.pdf"

EMAIL_HOST = "smtp.gmail.com"; EMAIL_PORT = 587
EMAIL_USER = "boletotravelinkeo@gmail.com"; EMAIL_PASS = "zqar oyma zdxk ylaj"
EMAIL_TO   = "travelinkeo@gmail.com"; EMAIL_CC = "boletotravelinkeo@gmail.com"

HTML_WRAP = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Space+Grotesk:wght@500;700&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter','Segoe UI',sans-serif;background:#fff;color:#1a1a2e;font-size:11.5px;line-height:1.8}}
.cover{{background:linear-gradient(135deg,#0a0d12 0%,#1a1035 50%,#0a0d12 100%);color:white;padding:70px 60px;min-height:460px;display:flex;flex-direction:column;justify-content:center;page-break-after:always;border-bottom:4px solid #8b5cf6}}
.cover .badge{{display:inline-block;background:rgba(139,92,246,.2);border:1px solid rgba(139,92,246,.4);color:#a78bfa;font-size:10px;font-weight:700;letter-spacing:.1em;padding:6px 14px;border-radius:20px;margin-bottom:24px;text-transform:uppercase}}
.cover h1{{font-family:'Space Grotesk',sans-serif;font-size:38px;font-weight:900;color:#fff;letter-spacing:-1px;margin-bottom:6px;line-height:1.1}}
.cover h1 span{{color:#8b5cf6}}
.cover .meta{{border-top:1px solid rgba(139,92,246,.3);padding-top:16px;margin-top:20px;font-size:11px;color:#64748b}}
.sep{{background:linear-gradient(135deg,#1a1035,#0f172a);color:white;padding:40px 55px;page-break-before:always;border-left:6px solid #8b5cf6;margin-bottom:0}}
.sep h2{{font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:900;color:#a78bfa;margin-bottom:6px}}
.sep p{{color:#94a3b8;font-size:12px}}
.content{{padding:36px 55px}}
h1{{font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:900;color:#0f1923;border-bottom:3px solid #8b5cf6;padding-bottom:8px;margin:40px 0 16px;page-break-before:always}}
h2{{font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#5b21b6;margin:24px 0 8px}}
h3{{font-size:13px;font-weight:700;color:#374151;margin:16px 0 5px}}
p{{margin:7px 0;color:#374151}}
blockquote{{background:#f5f3ff;border-left:4px solid #8b5cf6;padding:10px 14px;margin:10px 0;border-radius:0 8px 8px 0;color:#4c1d95;font-size:11px;font-style:italic}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:10.5px}}
thead th{{background:#1a1035;color:#a78bfa;padding:9px 11px;text-align:left;font-weight:700;font-size:9.5px;text-transform:uppercase;letter-spacing:.05em}}
tbody td{{padding:8px 11px;border-bottom:1px solid #e5e7eb;color:#374151}}
tbody tr:nth-child(odd){{background:#faf5ff}}
code{{background:#1a1035;color:#a78bfa;padding:2px 5px;border-radius:4px;font-family:'Courier New',monospace;font-size:9.5px}}
pre{{background:#0f0a1e;color:#e2e8f0;padding:14px;border-radius:8px;margin:10px 0;font-size:9.5px;border-left:3px solid #8b5cf6;white-space:pre-wrap;word-break:break-all}}
ul,ol{{padding-left:20px;margin:7px 0;color:#374151}}
li{{margin:3px 0}}
hr{{border:none;height:2px;background:linear-gradient(to right,#8b5cf6,transparent);margin:20px 0}}
strong{{color:#1a1a2e;font-weight:700}}
@page{{margin:18mm 14mm;size:A4;@bottom-center{{content:"TravelHub — Plan Estratégico Integral 2026  |  Pág. " counter(page);font-size:8px;color:#94a3b8}}@top-right{{content:"travelhub.cc";font-size:8px;color:#8b5cf6}}}}
</style></head><body>
<div class="cover">
  <div class="badge">Confidencial — Plan Estratégico Integral</div>
  <h1>TravelHub<br><span>Plan Completo 2026</span></h1>
  <p style="color:#c4b5fd;font-size:15px;margin:16px 0 30px;line-height:1.7">
    Tres documentos. Un solo mapa.<br>
    Diagnóstico · Go-To-Market · PMV + Sprint de Guerra
  </p>
  <div class="meta"><strong>Volumen 1:</strong> Análisis Estratégico &nbsp;·&nbsp; <strong>Volumen 2:</strong> Plan Complementario v2 &nbsp;·&nbsp; <strong>Volumen 3:</strong> PMV + Sprint de Guerra</div>
  <div class="meta" style="margin-top:10px"><strong>Emisión:</strong> Abril 2026 &nbsp;|&nbsp; <strong>Revisado:</strong> Análisis cruzado multi-AI &nbsp;|&nbsp; <strong>Versión:</strong> Final</div>
</div>
{body}
</body></html>"""

def convertir_md(path, titulo, num):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    cuerpo = markdown.markdown(txt, extensions=["tables","fenced_code","toc"])
    sep = f'<div class="sep"><h2>Volumen {num} — {titulo}</h2><p>Documento {num} de 3 del Plan Estratégico Integral TravelHub 2026</p></div>'
    return f'{sep}<div class="content">{cuerpo}</div>'

def generar_pdf():
    print("📄 Construyendo PDF unificado...")
    partes = [convertir_md(p, t, i+1) for i,(p,t) in enumerate(DOCS)]
    html   = HTML_WRAP.format(body="\n".join(partes))
    from weasyprint import HTML
    HTML(string=html).write_pdf(PDF_OUT)
    kb = os.path.getsize(PDF_OUT)/1024
    print(f"✅ PDF: {PDF_OUT} ({kb:.0f} KB)")

def enviar():
    print(f"📧 Enviando a {EMAIL_TO}...")
    msg = MIMEMultipart()
    msg["From"]    = f"TravelHub Strategy <{EMAIL_USER}>"
    msg["To"]      = EMAIL_TO; msg["Cc"] = EMAIL_CC
    msg["Subject"] = "📋 TravelHub — Plan Estratégico Completo 2026 (3 Volúmenes)"
    msg.attach(MIMEText("""
Hola Armando,

Adjunto el Plan Estratégico Completo de TravelHub en un solo PDF:

  Vol. 1 — Análisis Estratégico (diagnóstico técnico, producto, negocio)
  Vol. 2 — Plan Complementario v2 (GTM, métricas SaaS, momento AHA)
  Vol. 3 — PMV + Sprint de Guerra (12 semanas de ejecución semanal)

Este es el documento final. Los tres volúmenes juntos responden a:
  • ¿Dónde estamos? (Vol. 1)
  • ¿Cómo llegamos a los primeros clientes? (Vol. 2)
  • ¿Qué hacemos exactamente esta semana? (Vol. 3)

Frase clave del análisis cruzado:
"No necesitas más análisis. Necesitas menos features y más usuarios reales."

---
TravelHub ERP — travelhub.cc
    """.strip(), "plain", "utf-8"))
    with open(PDF_OUT,"rb") as f:
        p = MIMEBase("application","octet-stream"); p.set_payload(f.read())
        encoders.encode_base64(p)
        p.add_header("Content-Disposition",'attachment; filename="TravelHub_Plan_Completo_2026.pdf"')
        msg.attach(p)
    s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT); s.starttls(); s.login(EMAIL_USER, EMAIL_PASS)
    s.sendmail(EMAIL_USER, [EMAIL_TO, EMAIL_CC], msg.as_string()); s.quit()
    print(f"✅ Enviado a: {EMAIL_TO}, {EMAIL_CC}")

if __name__ == "__main__":
    print("="*55); print("  TravelHub — Generando Plan Completo 2026"); print("="*55)
    generar_pdf(); enviar()
    print("="*55)


#!/usr/bin/env python3
"""
Genera PDF del análisis estratégico de TravelHub y lo envía por correo.
"""
import os
import smtplib
import markdown
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

ANALISIS_MD = r"C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d\Analisis_Estrategico_TravelHub.md"
PDF_OUTPUT  = r"C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d\Analisis_Estrategico_TravelHub.pdf"

EMAIL_HOST  = "smtp.gmail.com"
EMAIL_PORT  = 587
EMAIL_USER  = "boletotravelinkeo@gmail.com"
EMAIL_PASS  = "zqar oyma zdxk ylaj"
EMAIL_TO    = "travelinkeo@gmail.com"
EMAIL_CC    = "boletotravelinkeo@gmail.com"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Space+Grotesk:wght@500;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', 'Segoe UI', sans-serif; background: #fff; color: #1a1a2e; font-size: 12px; line-height: 1.7; }}

  /* PORTADA */
  .cover {{
    background: linear-gradient(135deg, #0a0d12 0%, #1a1035 50%, #0a0d12 100%);
    color: white; padding: 70px 60px; min-height: 480px;
    display: flex; flex-direction: column; justify-content: center;
    page-break-after: always; border-bottom: 4px solid #8b5cf6;
  }}
  .cover .badge {{
    display: inline-block; background: rgba(139,92,246,0.2); border: 1px solid rgba(139,92,246,0.4);
    color: #a78bfa; font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
    padding: 6px 14px; border-radius: 20px; margin-bottom: 24px; text-transform: uppercase;
  }}
  .cover h1 {{ font-family: 'Space Grotesk', sans-serif; font-size: 42px; font-weight: 900;
    color: #ffffff; letter-spacing: -1px; margin-bottom: 8px; line-height: 1.1; }}
  .cover h1 span {{ color: #8b5cf6; }}
  .cover .subtitle {{ font-size: 18px; color: #94a3b8; margin-bottom: 40px; }}
  .cover .meta {{ border-top: 1px solid rgba(139,92,246,0.3); padding-top: 20px; margin-top: 20px;
    font-size: 12px; color: #64748b; }}
  .cover .meta strong {{ color: #8b5cf6; }}

  /* CONTENIDO */
  .content {{ padding: 40px 55px; }}
  h1 {{ font-family: 'Space Grotesk', sans-serif; font-size: 26px; font-weight: 900;
    color: #0f1923; border-bottom: 3px solid #8b5cf6; padding-bottom: 10px;
    margin: 45px 0 18px; page-break-before: always; }}
  h2 {{ font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 700;
    color: #5b21b6; margin: 28px 0 10px; }}
  h3 {{ font-size: 14px; font-weight: 700; color: #374151; margin: 18px 0 6px; }}
  p {{ margin: 8px 0; color: #374151; }}

  blockquote {{
    background: #f5f3ff; border-left: 4px solid #8b5cf6;
    padding: 12px 16px; margin: 12px 0; border-radius: 0 8px 8px 0;
    color: #4c1d95; font-size: 11.5px; font-style: italic;
  }}

  table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 11px; }}
  thead th {{ background: #1a1035; color: #a78bfa; padding: 10px 12px;
    text-align: left; font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; }}
  tbody td {{ padding: 9px 12px; border-bottom: 1px solid #e5e7eb; color: #374151; }}
  tbody tr:nth-child(odd) {{ background: #faf5ff; }}

  code {{ background: #1a1035; color: #a78bfa; padding: 2px 6px;
    border-radius: 4px; font-family: 'Courier New', monospace; font-size: 10px; }}
  pre {{ background: #0f0a1e; color: #e2e8f0; padding: 16px; border-radius: 8px;
    margin: 12px 0; font-size: 10px; border-left: 3px solid #8b5cf6; }}

  ul, ol {{ padding-left: 22px; margin: 8px 0; color: #374151; }}
  li {{ margin: 4px 0; }}
  hr {{ border: none; height: 2px; background: linear-gradient(to right, #8b5cf6, transparent); margin: 24px 0; }}
  strong {{ color: #1a1a2e; font-weight: 700; }}

  @page {{ margin: 20mm 15mm; size: A4;
    @bottom-center {{ content: "TravelHub — Análisis Estratégico Fundador 2026 | Pág. " counter(page);
      font-size: 9px; color: #94a3b8; }}
    @top-right {{ content: "travelhub.cc"; font-size: 9px; color: #8b5cf6; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <div class="badge">Confidencial — Solo para Fundadores</div>
  <h1>TravelHub<br><span>Análisis Estratégico</span></h1>
  <div class="subtitle">
    Perspectiva: CTO Fundador · Product Manager SaaS · Experto en Automatización
  </div>
  <p style="color:#c4b5fd; font-size:14px; line-height:1.6; margin-bottom:30px">
    Un diagnóstico honesto y sin filtros del producto, la arquitectura,<br>
    el modelo de negocio y el camino hacia el éxito real.
  </p>
  <div class="meta">
    <strong>Emisión:</strong> Abril 2026 &nbsp;|&nbsp;
    <strong>Sistema:</strong> TravelHub ERP v2026 &nbsp;|&nbsp;
    <strong>Clasificación:</strong> Estratégico / Confidencial
  </div>
</div>

<div class="content">
{content}
</div>

</body>
</html>
"""

def generar_pdf():
    print("📄 Leyendo análisis estratégico...")
    with open(ANALISIS_MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    print("🔄 Convirtiendo a HTML...")
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "toc"])
    full_html = HTML_TEMPLATE.format(content=html_body)

    print("📑 Generando PDF...")
    from weasyprint import HTML
    HTML(string=full_html).write_pdf(PDF_OUTPUT)
    kb = os.path.getsize(PDF_OUTPUT) / 1024
    print(f"✅ PDF listo: {PDF_OUTPUT} ({kb:.1f} KB)")
    return True

def enviar_correo():
    print(f"\n📧 Enviando a {EMAIL_TO}...")

    msg = MIMEMultipart()
    msg["From"]    = f"TravelHub Estrategia <{EMAIL_USER}>"
    msg["To"]      = EMAIL_TO
    msg["Cc"]      = EMAIL_CC
    msg["Subject"] = "🧠 TravelHub — Análisis Estratégico Fundador (PDF Adjunto)"

    cuerpo = """
Hola Armando,

Adjunto encuentras el Análisis Estratégico Completo de TravelHub, elaborado desde la
perspectiva de un CTO Fundador + Product Manager SaaS + Experto en Automatización.

El documento cubre 10 dimensiones:

  1. Visión General del Proyecto
  2. Arquitectura y Tecnología (evaluación técnica real)
  3. Producto y UX — Fricciones identificadas
  4. Automatización — Qué falta y qué diferencia
  5. Negocio y Modelo de Ingresos
  6. Ventas y Adopción
  7. Ventajas Competitivas
  8. Puntos Críticos (sin filtros)
  9. Plan de Acción — Corto, mediano y largo plazo
  10. Ideas Avanzadas que pueden romper el mercado

Es un diagnóstico honesto. No suaviza críticas.
El objetivo es que TravelHub sea un éxito real.

---
TravelHub ERP — Generado automáticamente
travelhub.cc
    """.strip()

    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    with open(PDF_OUTPUT, "rb") as f:
        parte = MIMEBase("application", "octet-stream")
        parte.set_payload(f.read())
        encoders.encode_base64(parte)
        parte.add_header("Content-Disposition", 'attachment; filename="Analisis_Estrategico_TravelHub_2026.pdf"')
        msg.attach(parte)

    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, [EMAIL_TO, EMAIL_CC], msg.as_string())
    server.quit()
    print(f"✅ Correo enviado a: {EMAIL_TO}, {EMAIL_CC}")

if __name__ == "__main__":
    print("=" * 52)
    print("  TravelHub — Envío de Análisis Estratégico")
    print("=" * 52)
    if generar_pdf():
        enviar_correo()
    print("=" * 52)

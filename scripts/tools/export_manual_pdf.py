
#!/usr/bin/env python3
"""
Script para generar el Manual de TravelHub en PDF y enviarlo por correo.
"""
import os
import sys
import smtplib
import markdown
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MANUAL_MD_PATH = r"C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d\Manual_TravelHub_Biblia_Cuento.md"
SCREENSHOTS_DIR = r"C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d"
PDF_OUTPUT = r"C:\Users\ARMANDO\.gemini\antigravity\brain\5e11f3b7-df37-4e76-b5cc-2a2e63d18f1d\Manual_TravelHub_2026_Completo.pdf"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "boletotravelinkeo@gmail.com"
EMAIL_PASS = "zqar oyma zdxk ylaj"
EMAIL_TO   = "travelinkeo@gmail.com"
EMAIL_CC   = "boletotravelinkeo@gmail.com"
# ───────────────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Space+Grotesk:wght@500;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
    background: #ffffff;
    color: #1a1a2e;
    font-size: 12px;
    line-height: 1.6;
  }}

  /* PORTADA */
  .cover {{
    background: linear-gradient(135deg, #0a0d12 0%, #0f3d2e 50%, #0a0d12 100%);
    color: white;
    padding: 80px 60px;
    min-height: 500px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    page-break-after: always;
    border-bottom: 4px solid #10b981;
  }}
  .cover h1 {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 48px;
    font-weight: 900;
    color: #10b981 !important;
    letter-spacing: -1px;
    margin-bottom: 10px;
  }}
  .cover .subtitle {{
    font-size: 20px;
    color: #94a3b8;
    margin-bottom: 40px;
    font-weight: 400;
  }}
  .cover .tagline {{
    font-size: 14px;
    color: #64748b;
    border-top: 1px solid rgba(16,185,129,0.3);
    padding-top: 20px;
    margin-top: 20px;
  }}
  .cover .logo-area {{
    width: 80px; height: 80px;
    background: #10b981;
    border-radius: 20px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 30px;
    font-size: 32px; font-weight: 900; color: white;
  }}

  /* CONTENIDO */
  .content {{
    padding: 40px 60px;
  }}

  h1, h2, h3, h4 {{
    color: #0f1923 !important;
    font-family: 'Space Grotesk', sans-serif;
  }}
  h1 {{ font-size: 28px; margin: 40px 0 15px; border-bottom: 3px solid #10b981; padding-bottom: 10px; page-break-before: always; }}
  h2 {{ font-size: 20px; margin: 30px 0 10px; color: #10b981 !important; }}
  h3 {{ font-size: 16px; margin: 20px 0 8px; color: #065f46 !important; }}
  h4 {{ font-size: 13px; margin: 15px 0 6px; }}

  p {{ margin: 8px 0; color: #374151; }}

  blockquote {{
    background: #f0fdf4;
    border-left: 4px solid #10b981;
    padding: 12px 16px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
    color: #065f46;
    font-size: 11px;
  }}
  blockquote strong {{ color: #064e3b; }}

  /* ADVERTENCIA */
  blockquote:has(strong:first-child > em) {{
    background: #fff7ed;
    border-color: #f97316;
    color: #9a3412;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 11px;
  }}
  thead th {{
    background: #0f1923;
    color: #10b981;
    padding: 10px 12px;
    text-align: left;
    font-weight: 700;
    letter-spacing: 0.05em;
    font-size: 10px;
    text-transform: uppercase;
  }}
  tbody td {{
    padding: 9px 12px;
    border-bottom: 1px solid #e5e7eb;
    color: #374151;
  }}
  tbody tr:nth-child(odd) {{ background: #f9fafb; }}
  tbody tr:hover {{ background: #f0fdf4; }}

  code {{
    background: #0f1923;
    color: #10b981;
    padding: 1px 6px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
  }}
  pre {{
    background: #0f1923;
    color: #e2e8f0;
    padding: 16px;
    border-radius: 8px;
    overflow: auto;
    font-size: 10px;
    margin: 12px 0;
    border-left: 3px solid #10b981;
  }}

  ul, ol {{
    padding-left: 24px;
    margin: 8px 0;
    color: #374151;
  }}
  li {{ margin: 4px 0; }}

  img {{
    max-width: 100%;
    border-radius: 12px;
    border: 2px solid #e5e7eb;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    margin: 12px 0;
  }}

  hr {{
    border: none;
    height: 2px;
    background: linear-gradient(to right, #10b981, transparent);
    margin: 25px 0;
  }}

  /* INDICE */
  .toc-section {{
    background: #0a0d12;
    color: white;
    padding: 40px;
    border-radius: 16px;
    margin: 20px 0;
  }}
  .toc-section h2 {{ color: #10b981 !important; margin-bottom: 20px; }}

  @page {{
    margin: 20mm 15mm;
    size: A4;
    @bottom-center {{
      content: "TravelHub — Manual de Usuario 2026 | Página " counter(page);
      font-size: 9px;
      color: #94a3b8;
    }}
    @top-right {{
      content: "✈ travelhub.cc";
      font-size: 9px;
      color: #10b981;
    }}
  }}
</style>
</head>
<body>

<div class="cover">
  <div class="logo-area">TH</div>
  <h1>📖 Manual de Usuario</h1>
  <div class="subtitle">TravelHub — La Biblia Completa</div>
  <p style="color:#a7f3d0; font-size:16px; margin-bottom: 20px">
    Tu guía paso a paso para dominar la plataforma desde cero.<br>
    Para cualquier persona. Sin conocimiento técnico previo.
  </p>
  <div class="tagline">
    ✈ travelhub.cc &nbsp;|&nbsp; Version 2026 &nbsp;|&nbsp; Actualizado Abril 2026<br>
    <span style="color:#10b981">13 Capítulos · Explicaciones simples · Screenshots reales del sistema</span>
  </div>
</div>

<div class="content">
{content}
</div>

</body>
</html>
"""

def generar_pdf():
    print("📄 Leyendo el manual en Markdown...")
    with open(MANUAL_MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Reemplazar referencias a screenshots locales con rutas absolutas
    screenshots = {
        "manual_dashboard_20260410_212450_1775870722868.png": os.path.join(SCREENSHOTS_DIR, "manual_dashboard_20260410_212450_1775870722868.png"),
        "manual_vuelos_20260410_212411_1775870686412.png": os.path.join(SCREENSHOTS_DIR, "manual_vuelos_20260410_212411_1775870686412.png"),
        "manual_clientes_20260410_212620_1775870975807.png": os.path.join(SCREENSHOTS_DIR, "manual_clientes_20260410_212620_1775870975807.png"),
        "manual_cotizaciones_20260410_212900_1775871084459.png": os.path.join(SCREENSHOTS_DIR, "manual_cotizaciones_20260410_212900_1775871084459.png"),
        "manual_boletos_20260410_213100_1775871179742.png": os.path.join(SCREENSHOTS_DIR, "manual_boletos_20260410_213100_1775871179742.png"),
    }
    for fname, fpath in screenshots.items():
        if os.path.exists(fpath):
            abs_uri = Path(fpath).as_uri()
            md_text = md_text.replace(fname, abs_uri)

    print("🔄 Convirtiendo Markdown a HTML...")
    html_content = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "attr_list"]
    )

    full_html = HTML_TEMPLATE.format(content=html_content)

    print("📑 Generando PDF con WeasyPrint...")
    try:
        from weasyprint import HTML, CSS
        HTML(string=full_html, base_url=SCREENSHOTS_DIR).write_pdf(PDF_OUTPUT)
        size_kb = os.path.getsize(PDF_OUTPUT) / 1024
        print(f"✅ PDF generado: {PDF_OUTPUT} ({size_kb:.1f} KB)")
        return True
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        return False


def enviar_correo():
    print(f"\n📧 Enviando correo a {EMAIL_TO}...")

    msg = MIMEMultipart()
    msg["From"] = f"TravelHub Sistema <{EMAIL_USER}>"
    msg["To"] = EMAIL_TO
    msg["Cc"] = EMAIL_CC
    msg["Subject"] = "📖 Manual TravelHub — La Biblia Completa Edición Cuento (PDF)"

    body = """
Hola,

Adjunto encontrarás el Manual de Usuario Completo de TravelHub en formato PDF.

📖 Este manual incluye:
  ✅ 13 capítulos explicados de forma sencilla
  ✅ Screenshots reales del sistema
  ✅ Guía paso a paso desde el primer login
  ✅ Explicación de todos los módulos: Vuelos, Boletos, Clientes, Ventas, Finanzas, IA y más
  ✅ Preguntas frecuentes y solución de problemas comunes

Fue diseñado para que cualquier persona, independientemente de su nivel técnico, pueda usar la plataforma desde cero.

📌 Versión: 2026 | Actualizado: Abril 2026
🌐 Acceso al sistema: https://travelhub.cc

---
Este mensaje fue generado automáticamente por TravelHub ERP.
    """.strip()

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Adjuntar PDF
    with open(PDF_OUTPUT, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="Manual_TravelHub_2026_Completo.pdf"')
        msg.attach(part)

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        recipients = [EMAIL_TO, EMAIL_CC]
        server.sendmail(EMAIL_USER, recipients, msg.as_string())
        server.quit()
        print(f"✅ Correo enviado exitosamente a: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False


if __name__ == "__main__":
    print("=" * 55)
    print("  TRAVELHUB — Generador de Manual PDF y Envío de Correo")
    print("=" * 55)

    if generar_pdf():
        enviar_correo()
    else:
        print("❌ No se pudo generar el PDF. Abortando envío.")

    print("\n" + "=" * 55)
    print("  Proceso completado.")
    print("=" * 55)

import os
import re

SOURCE_DIR = r"C:\Users\ARMANDO\Downloads\stitch_swiss_light_quote_creator_form"
TARGET_DIR = r"C:\Users\ARMANDO\travelhub_project\core\templates\core\tickets"

templates_to_process = {
    "ticket_template_kiu_bolivares.html_1.html": "ticket_template_kiu_bolivares.html",
    "ticket_template_sabre.html": "ticket_template_sabre.html",
    "ticket_template_copa_sprk.html": "ticket_template_copa_sprk.html",
    "ticket_template_tk_connect.html": "ticket_template_tk_connect.html",
    "ticket_template_wingo.html": "ticket_template_wingo.html"
}

def process_template(content):
    # Inyectar logo dinamico (Jinja2 syntax)
    img_pattern = re.compile(r'<img\s+class="logo"\s+src="(.*?)"\s+alt="(.*?)">', re.DOTALL)
    def repl_img(match):
        default_src = match.group(1)
        alt_text = match.group(2)
        return f"""{{% if agencia and agencia.logo_base64 %}}
                <img class="logo" src="{{{{ agencia.logo_base64 }}}}" alt="{alt_text}">
            {{% else %}}
                <img class="logo" src="{default_src}" alt="{alt_text}">
            {{% endif %}}"""
    content = img_pattern.sub(repl_img, content)
    
    # Inyectar variables de color de Agencia (Theme Config)
    if "{% if agencia %}" not in content:
        css_injection = """
        {% if agencia %}
        :root {
            {% if agencia.color_primario %}--tk-dark-blue: {{ agencia.color_primario }};{% endif %}
            {% if agencia.color_secundario %}--tk-medium-blue: {{ agencia.color_secundario }};{% endif %}
        }
        {% endif %}
        """
        content = content.replace("</style>", css_injection + "</style>")
    
    # Reemplazar contacto (Jinja2 syntax)
    contact_pattern = re.compile(r'<div class="header-contact">.*?(?:TELEFONO|INFO).*?</div>', re.DOTALL | re.IGNORECASE)
    def repl_contact(match):
         return """<div class="header-contact">
                TELEFONO: {{ agencia.telefono | default('+58 000 000 0000') }}<br>
                MAIL INFO: {{ agencia.email | default('info@agencia.com') | upper }}
            </div>"""
    content = contact_pattern.sub(repl_contact, content)
    
    # Reemplazar footer (Jinja2 syntax)
    footer_pattern = re.compile(r'<footer class="ticket-footer">.*?</footer>', re.DOTALL | re.IGNORECASE)
    def repl_footer(match):
         return """<footer class="ticket-footer">
            <div class="thank-you">Gracias por elegirnos. ¡Te deseamos un excelente viaje!</div>
            @{{ agencia.nombre | default('AGENCIA') | upper }} | {{ agencia.telefono | default('+58 000 000 0000') }} | {{ agencia.direccion | default('S/D') | upper }}
        </footer>"""
    content = footer_pattern.sub(repl_footer, content)
    
    return content

os.makedirs(TARGET_DIR, exist_ok=True)

for src_name, tgt_name in templates_to_process.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    tgt_path = os.path.join(TARGET_DIR, tgt_name)
    
    if os.path.exists(src_path):
        with open(src_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = process_template(content)
        
        with open(tgt_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Migrado y adaptado JINJA2: {tgt_name}")
    else:
        print(f"⚠️ Archivo fuente no encontrado: {src_name}")

print("Proceso finalizado.")

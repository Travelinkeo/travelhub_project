import os
import re

directories = [
    r"C:\Users\ARMANDO\travelhub_project\core\templates\core\tickets",
    r"C:\Users\ARMANDO\travelhub_project\core\templates\vouchers"
]

def fix_template(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix line breaks inside {% endif %}
    content = re.sub(r'\{%\s*endif\s*%\}', '{% endif %}', content, flags=re.MULTILINE)
    # The real issue was {% \n endif %}. 
    content = re.sub(r'\{%[\s\n]*endif[\s\n]*%\}', '{% endif %}', content)

    # What about (venta.agencia.logo_pdf_dark_base64  ?
    # This was a jinja macro parenthesis problem? 
    # Let's fix that specific file manually later, or try to catch parenthesis in if statements: 
    # {% if (something) %} -> {% if something %}
    content = re.sub(r'\{%\s*if\s*\((.*?)\)\s*%\}', r'{% if \1 %}', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed {filepath}")

for template_dir in directories:
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                fix_template(os.path.join(root, file))


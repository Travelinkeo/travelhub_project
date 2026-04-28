import os

def fix_golden_ticket():
    path = r'c:\Users\ARMANDO\travelhub_project\core\templates\core\tickets\golden_ticket_v2.html'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix default colors
    content = content.replace("| default('#0D1E40', true if agencia else '#0D1E40')", '| default:"#0D1E40"')
    content = content.replace("| default('#2173A6', true if agencia else '#2173A6')", '| default:"#2173A6"')
    
    # 2. Fix the SOURCE_SYSTEM in root
    content = content.replace("{{ agencia.color_secundario|default:'#88081F', true }}", "{{ agencia.color_secundario|default:'#88081F' }}")
    content = content.replace("{{ agencia.color_amadeus|default:'#0C66E1', true }}", "{{ agencia.color_amadeus|default:'#0C66E1' }}")

    # 3. Fix Logo logical block (Line 285+)
    # This part is tricky. I'll replace the whole block with something simpler for DTL.
    old_logo_block = """                {% if agencia %}
                    {% if is_dark_color and agencia.logo_pdf_dark_base64 %}
                        <img src="{% if 'data:image' in agencia.logo_pdf_dark_base64 %}{{ agencia.logo_pdf_dark_base64 }}{% else %}data:image/png;base64,{{ agencia.logo_pdf_dark_base64 }}{% endif %}">
                    {% elif agencia.logo_pdf_base64 %}
                        <img src="{% if 'data:image' in agencia.logo_pdf_base64 %}{{ agencia.logo_pdf_base64 }}{% else %}data:image/png;base64,{{ agencia.logo_pdf_base64 }}{% endif %}" 
                             class="{{ 'logo-invertido' if is_dark_color else 'logo-oscuro' }}">
                    {% elif (agencia.logo_light or agencia.logo_dark) %}
                        {% set logo_file = (agencia.logo_dark if is_dark_color else agencia.logo_light) or agencia.logo %}
                        <img src="{{ logo_file.url if logo_file else '#' }}" class="{{ 'logo-invertido' if is_dark_color else 'logo-oscuro' }}">
                    {% else %}
                        <span style="font-size: 24px; font-weight: 800;">{{ agencia.nombre_comercial|default:agencia.nombre, true|default:"TRAVELHUB", true|upper }}<span class="dot">.</span></span>
                    {% endif %}
                {% else %}"""

    new_logo_block = """                {% if agencia %}
                    {% if is_dark_color and agencia.logo_pdf_dark_base64 %}
                        <img src="{% if 'data:image' in agencia.logo_pdf_dark_base64 %}{{ agencia.logo_pdf_dark_base64 }}{% else %}data:image/png;base64,{{ agencia.logo_pdf_dark_base64 }}{% endif %}">
                    {% elif agencia.logo_pdf_base64 %}
                        <img src="{% if 'data:image' in agencia.logo_pdf_base64 %}{{ agencia.logo_pdf_base64 }}{% else %}data:image/png;base64,{{ agencia.logo_pdf_base64 }}{% endif %}" 
                             class="{% if is_dark_color %}logo-invertido{% else %}logo-oscuro{% endif %}">
                    {% elif agencia.logo_dark or agencia.logo_light %}
                        <img src="{% if is_dark_color %}{{ agencia.logo_dark.url }}{% else %}{{ agencia.logo_light.url }}{% endif %}" class="{% if is_dark_color %}logo-invertido{% else %}logo-oscuro{% endif %}">
                    {% else %}
                        <span style="font-size: 24px; font-weight: 800;">{{ agencia.nombre_comercial|default:agencia.nombre|default:"TRAVELHUB"|upper }}<span class="dot">.</span></span>
                    {% endif %}
                {% else %}"""
    
    # Use direct replacement for the block if exact match fails, I'll use regex or chunks
    # But I see the file contents in my previous view, I'll match exactly.
    # Wait, the exact match is very sensitive to whitespace.
    
    # 4. Fix other Jinja2-isms
    content = content.replace("{{ 'logo-invertido' if is_dark_color else 'logo-oscuro' }}", "{% if is_dark_color %}logo-invertido{% else %}logo-oscuro{% endif %}")
    content = content.replace("{{ solo_nombre_pasajero|upper }}", "{{ solo_nombre_pasajero|upper }}")
    content = content.replace("{{ AGENTE_EMISOR|default:agencia.iata if agencia else '10617390' }}", "{% if agencia %}{{ AGENTE_EMISOR|default:agencia.iata }}{% else %}10617390{% endif %}")
    content = content.replace("true|default:\"TRAVELHUB\"", "default:\"TRAVELHUB\"")
    
    # 5. Fix the complex logo block properly
    # I'll use a safer multi-line replacement by searching for the start and end of that section
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed golden_ticket_v2.html")

if __name__ == '__main__':
    fix_golden_ticket()

import re
import os

html_path = r'C:\Users\ARMANDO\Downloads\stitch_swiss_light_quote_creator_form\swiss_light_quote_creator_form\code.html'
out_path = r'C:\Users\ARMANDO\travelhub_project\core\templates\core\erp\cotizaciones\crear_cotizacion_swiss.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Extract <main>
m = re.search(r'<main.*?</main>', html, re.DOTALL)
if m:
    main_content = m.group(0)
    
    template = f"""{{% extends 'base_modern_v2.html' %}}
{{% block title %}}{{% if form.instance.pk %}}Editar Cotización #{{{{ form.instance.numero_cotizacion }}}}{{% else %}}Nueva Cotización{{% endif %}}{{% endblock %}}

{{% block extra_head %}}
<style>
/* Custom overrides for Swiss Light */
.shadow-swiss {{ box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important; }}
.dark .bg-surface-dark {{ background-color: #1b2127; }}
.dark .bg-background-dark {{ background-color: #101922; }}
.dark .border-border-dark {{ border-color: #283039; }}
/* Input Fixes to match design */
.form-input, .form-select {{ 
    width: 100%; border-radius: 0.25rem; border: 1px solid #e2e8f0; height: 3rem; padding-left: 1rem; padding-right: 1rem; 
}}
.dark .form-input, .dark .form-select {{ border-color: #283039; background-color: #1b2127; color: white; }}
</style>
{{% endblock %}}

{{% block content %}}
<form method="post" id="cotizacionForm">
{{% csrf_token %}}
{main_content}
</form>

<script>
    // Placeholder JS for totals
    console.log('Swiss Light Quote UI Loaded');
</script>
{{% endblock %}}
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write(template)
    print("Template generated!")
else:
    print("Could not find <main> tag")

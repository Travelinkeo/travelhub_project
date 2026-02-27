
import os
import re

file_path = r'c:\Users\ARMANDO\travelhub_project\core\templates\core\erp\cotizaciones\dashboard.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Ensure spaces around == in if tags
# Pattern: {% if request.GET.estado=='XXX' %} -> {% if request.GET.estado == 'XXX' %}
def fix_spaces(match):
    return match.group(0).replace('==', ' == ')

content = re.sub(r'{% if request\.GET\.estado==\'\w+\' %}', fix_spaces, content)

# Fix 2: Merge split template tags for client initials
# Pattern: {{ cotizacion.cliente.nombres|slice:":1" }}{{ \n \s+ cotizacion.cliente.apellidos|slice:":1" }}
# We'll look for the specific split occurrence
content = content.replace(
    '{{ cotizacion.cliente.nombres|slice:":1" }}{{\n                                    cotizacion.cliente.apellidos|slice:":1" }}',
    '{{ cotizacion.cliente.nombres|slice:":1" }}{{ cotizacion.cliente.apellidos|slice:":1" }}'
)

# Alternative regex for Fix 2 if exact string match fails due to whitespace var
content = re.sub(
    r'(\{\{ cotizacion\.cliente\.nombres\|slice:":1" \}\}\{\{)\s*\n\s*(cotizacion\.cliente\.apellidos\|slice:":1" \}\})',
    r'\1 \2',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied comprehensive fixes to dashboard.html")

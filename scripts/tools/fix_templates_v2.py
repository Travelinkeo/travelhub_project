import os
import re

directories = [
    r"C:\Users\ARMANDO\travelhub_project\core\templates\core\tickets",
    r"C:\Users\ARMANDO\travelhub_project\core\templates\vouchers"
]

def fix_template(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix default filter syntax: default('N/A') -> default:'N/A'
    def replace_default(match):
        inner = match.group(1).strip()
        return f'default:{inner}'
    content = re.sub(r'default\s*\(\s*(.*?)\s*\)', replace_default, content)

    # 2. Fix variable slicing: flight.origen[:3] -> flight.origen|slice:":3"
    def replace_slice(match):
        var = match.group(1)
        slc = match.group(2)
        return f'{var}|slice:"{slc}"'
    content = re.sub(r'([a-zA-Z0-9_\.]+)\s*\[\s*(:?\d*:?\d*)\s*\]', replace_slice, content)

    # 3. Fix dictionary access in templates: vuelo['fecha_salida'] -> vuelo.fecha_salida
    # Match ['something'] or ["something"]
    content = re.sub(r'\[[\'"]([a-zA-Z0-9_\.]+)[\'"]\]', r'.\1', content)

    # 4. Fix split()[0] -> we will just remove .split()[0] and output the full string for now so it doesn't crash 
    content = content.replace('.split()[0]', '')

    # 5. Fix logical OR in print statement: {{ flight.fecha or flight.fecha_salida }} -> {{ flight.fecha|default:flight.fecha_salida }}
    # Need to find {{ a or b }}
    def replace_or(match):
        a = match.group(1).strip()
        b = match.group(2).strip()
        # what if there are filters? flight.fecha|default:'N/A' or flight.fecha_salida
        # let's just do a simple replacement
        return f'{{{{ {a}|default:{b} }}}}'
    content = re.sub(r'\{\{\s*([^|{}]+?)\s+or\s+([^{}]+?)\s*\}\}', replace_or, content)

    # Note: re.sub above might be tricky if a has filters. Let's do a more robust approach just searching for " or " inside {{ }}
    # We can do this manually for the specific instance known: flight.fecha or flight.fecha_salida
    content = content.replace('flight.fecha or flight.fecha_salida', 'flight.fecha|default:flight.fecha_salida')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed {filepath}")

for template_dir in directories:
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                fix_template(os.path.join(root, file))


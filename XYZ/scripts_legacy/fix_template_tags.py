import re
import os

file_path = r'c:\Users\ARMANDO\travelhub_project\cotizaciones\templates\cotizaciones\plantilla_cotizacion.html'

def clean_tags(content):
    # Fix split {% ... %} tags
    # Example: {% \n else %} -> {% else %}
    content = re.sub(r'\{%\s*\n\s+', '{% ', content)
    content = re.sub(r'\s*\n\s+%\}', ' %}', content)
    
    # Fix split {{ ... }} tags
    # Example: {{ \n val }} -> {{ val }}
    content = re.sub(r'\{\{\s*\n\s+', '{{ ', content)
    content = re.sub(r'\s*\n\s+\}\}', ' }}', content)
    
    # Specific fix for the messy default filters that might span lines
    # Example: |default:"su \n destino"
    content = re.sub(r'\|default:"([^"]+)\n\s+([^"]+)"', r'|default:"\1 \2"', content)
    
    # Consolidate multiple spaces
    content = re.sub(r'\{%([^\n]+)%\}', lambda m: '{%' + ' '.join(m.group(1).split()) + '%}', content)
    content = re.sub(r'\{\{([^\n]+)\}\}', lambda m: '{{' + ' '.join(m.group(1).split()) + '}}', content)

    return content

if __name__ == "__main__":
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        exit(1)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        original = f.read()
        
    cleaned = clean_tags(original)
    
    if original == cleaned:
        print("No changes needed.")
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        print("Successfully cleaned template tags.")

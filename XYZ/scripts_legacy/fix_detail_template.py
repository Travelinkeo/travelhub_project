
import re

file_path = r'c:\Users\ARMANDO\travelhub_project\core\templates\core\erp\cotizaciones\detalle.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find tags spread across lines
# {{ \n \s+ var }} -> {{ var }}
def compact_tag(match):
    # Remove newlines and extra spaces inside the tag
    inner = match.group(0)
    # Replace newlines with spaces
    flat = inner.replace('\n', ' ')
    # Normalize whitespace (replace multiple spaces with single space)
    flat = re.sub(r'\s+', ' ', flat)
    return flat

# Regex for {{ ... }} that might span multiple lines
# We use non-greedy matching for content inside
content = re.sub(r'\{\{.*?\}\}', compact_tag, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Compacted tags in {file_path}")

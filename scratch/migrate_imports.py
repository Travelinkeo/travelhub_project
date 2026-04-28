import os
import re

patterns = [
    (r'from apps.contabilidad', 'from apps.contabilidad'),
    (r'import contabilidad(\.| )', r'import apps.contabilidad\1'),
    (r'from apps.cotizaciones', 'from apps.cotizaciones'),
    (r'import cotizaciones(\.| )', r'import apps.cotizaciones\1'),
    (r'from apps.accounting_assistant', 'from apps.accounting_assistant'),
    (r'import accounting_assistant(\.| )', r'import apps.accounting_assistant\1'),
]

root_dir = r'c:\Users\ARMANDO\travelhub_project'
exclude_dirs = {'.git', '.venv', 'venv', '__pycache__', 'staticfiles', 'media'}

def migrate_imports():
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py') or file.endswith('.md'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    for pattern, replacement in patterns:
                        new_content = re.sub(pattern, replacement, new_content)
                    
                    if new_content != content:
                        print(f"Migrating: {file_path}")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    migrate_imports()

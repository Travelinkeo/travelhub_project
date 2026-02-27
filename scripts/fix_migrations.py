import os
import re

def fix_migrations(dir_path):
    for f in os.listdir(dir_path):
        if not f.endswith('.py'):
            continue
        
        file_path = os.path.join(dir_path, f)
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace dependency tuples: ("personas", "xxxx") -> ("crm", "0001_initial")
        # Handle both single and double quotes
        new_content = re.sub(r'\((?:\'|")personas(?:\'|"),\s*(?:\'|")[^\'"]+(?:\'|")\)', '("crm", "0001_initial")', content)
        
        # Replace model references: "personas.Cliente" -> "crm.Cliente"
        # Preserve the quote type (single or double)
        new_content = re.sub(r"(['\"])personas\.", r"\1crm.", new_content)
        
        if new_content != content:
            print(f"Fixing {f}")
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)

if __name__ == "__main__":
    fix_migrations('core/migrations')
    fix_migrations('cotizaciones/migrations') # Just in case I missed anything

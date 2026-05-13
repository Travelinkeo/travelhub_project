import os

TESTS_DIR = 'tests'

REPLACEMENTS = {
    'from apps.automation.parsers.sabre_parser import': 'from apps.automation.parsers.legacy.sabre_parser import',
    'from apps.automation.parsers.legacy.base_parser import': 'from apps.automation.parsers.base_parser import',
    'from core.models.facturacion_consolidada import': 'from apps.finance.models import',
    'from core import pdf_generator': 'from apps.automation.parsers import pdf_generation as pdf_generator',
    'from core.pdf_generator import': 'from apps.automation.parsers.pdf_generation import',
    'from apps.automation.parsers.ticket_parser import': 'from apps.automation.services.ticket_parser_service import'
}

def fix_imports():
    archivos_modificados = 0
    for root, _dirs, files in os.walk(TESTS_DIR):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, encoding='utf-8') as f:
                        content = f.read()
                    original_content = content
                    for old_text, new_text in REPLACEMENTS.items():
                        content = content.replace(old_text, new_text)
                    if content != original_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"[OK] Import arreglado en: {filepath}")
                        archivos_modificados += 1
                except Exception as e:
                    print(f"[WARN] Error leyendo {filepath}: {e}")
    print(f"\nOperación finalizada. {archivos_modificados} archivos actualizados.")

if __name__ == '__main__':
    print("Iniciando escaneo y reparacion de imports en los tests...\n")
    fix_imports()
    print("\nListo! Ejecuta 'pytest -v' para comprobar.")
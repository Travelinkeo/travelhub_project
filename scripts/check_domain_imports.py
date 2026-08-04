# scripts/check_domain_imports.py
import ast
import sys
from pathlib import Path

# El directorio raíz del proyecto, asumimos que es dos niveles por encima de este script
# (scripts/check_domain_imports.py -> project_root/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPS_DIR = PROJECT_ROOT / "apps"


def get_domain_from_path(file_path, apps_dir):
    """
    Determina a qué dominio de la carpeta 'apps' pertenece un archivo.
    Ej: /path/to/project/apps/bookings/services.py -> 'bookings'
    """
    try:
        # Crea una ruta relativa desde el directorio de apps
        relative_path = Path(file_path).resolve().relative_to(apps_dir)
        # El primer componente de la ruta relativa es el nombre del dominio
        return relative_path.parts[0]
    except (ValueError, IndexError):
        # Si el archivo no está dentro de 'apps', no pertenece a ningún dominio
        return None


class ImportVisitor(ast.NodeVisitor):
    """
    Un visitante de AST que recopila todas las importaciones de un módulo.
    """

    def __init__(self):
        """__init__."""
        self.imports = []

    def visit_Import(self, node):
        """visit_Import."""
        for alias in node.names:
            self.imports.append((alias.name, node.lineno))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """visit_ImportFrom."""
        # node.module es None para importaciones relativas como 'from . import models'
        if node.module:
            self.imports.append((node.module, node.lineno))
        self.generic_visit(node)


def analyze_file(file_path):
    """
    Analiza un único archivo en busca de importaciones y devuelve una lista de ellas.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
        visitor = ImportVisitor()
        visitor.visit(tree)
        return visitor.imports
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        return []


# Definir matriz de dependencias permitidas para cada módulo de dominio
# Permite un diseño en capas (downstream depende de upstream) y utilidades compartidas.
ALLOWED_DEPENDENCIES = {
    "bookings": {"crm", "common", "communications", "finance", "automation"},
    "cotizaciones": {
        "crm",
        "bookings",
        "common",
        "communications",
        "automation",
        "finance",
        "contabilidad",
    },
    "finance": {"bookings", "crm", "common", "communications"},
    "contabilidad": {"finance", "bookings", "crm", "common", "communications"},
    "automation": {"bookings", "finance", "crm", "contabilidad", "common", "communications"},
    "accounting_assistant": {
        "bookings",
        "finance",
        "crm",
        "contabilidad",
        "common",
        "communications",
        "cotizaciones",
        "marketing",
        "cms",
        "automation",
    },
    "marketing": {"crm", "common", "communications", "bookings", "automation"},
    "cms": {"common", "communications"},
    "crm": {"common", "communications", "automation"},
    "common": {
        "communications",
        "bookings",
        "finance",
        "crm",
        "automation",
        "contabilidad",
        "cotizaciones",
    },
    "communications": {"common", "bookings", "automation"},
}

# Core internal paths that apps are allowed to import from.
# These are considered the "public API" of core for app-level usage.
ALLOWED_CORE_IMPORTS = {
    "core.api",
    "core.api.*",
    "core.middleware",
    "core.middleware.*",
    "core.models",
    "core.models.*",
    "core.context_processors",
    "core.auth_helpers",
    "core.tasks",
    "core.tasks.*",
    "core.forms",
    "core.forms.*",
    "core.fields",
    "core.fields.*",
    "core.signals",
    "core.signals.*",
    "core.exceptions",
    "core.serializers",
    "core.serializers.*",
}


def main(files_to_check):
    """
    Función principal que orquesta el análisis de los archivos.
    """
    illegal_imports_found = False

    # Obtener la lista de dominios de primer nivel en la carpeta 'apps'
    try:
        domain_names = [
            d.name for d in APPS_DIR.iterdir() if d.is_dir() and not d.name.startswith("__")
        ]
    except FileNotFoundError:
        print(f"Error: El directorio de apps '{APPS_DIR}' no fue encontrado.", file=sys.stderr)
        return 1

    for file_path in files_to_check:
        # Solo nos interesan los archivos dentro de la carpeta 'apps'
        if str(APPS_DIR) not in str(Path(file_path).resolve()):
            continue

        current_domain = get_domain_from_path(file_path, APPS_DIR)
        if not current_domain:
            continue

        imports = analyze_file(file_path)

        for imported_module, line_number in imports:
            # Comprobar si la importación es de otro dominio de 'apps'
            # Ej: 'apps.finance.services'
            if imported_module.startswith("apps."):
                parts = imported_module.split(".")
                # parts[0] es 'apps', parts[1] es el nombre del dominio importado
                if len(parts) > 1:
                    imported_domain = parts[1]
                    # Es una importación ilegal si el dominio importado está en nuestra lista
                    # y no es el dominio actual ni está en la lista de permitidos.
                    if imported_domain in domain_names and imported_domain != current_domain:
                        allowed = ALLOWED_DEPENDENCIES.get(current_domain, set())
                        if imported_domain not in allowed:
                            print(
                                f"ERROR: Importación ilegal encontrada en '{file_path}' (línea {line_number}).\n"
                                f"  -> El módulo '{current_domain}' no puede importar desde '{imported_domain}'.\n"
                                f"  -> Línea conflictiva: `import {imported_module}` o `from {imported_module} ...`\n"
                                f"  -> Razón: Viola las reglas de arquitectura del Manifiesto. Usa señales o eventos en su lugar.",
                                file=sys.stderr,
                            )
                            illegal_imports_found = True

            # Comprobar si la importación va al núcleo de forma directa (y no por core.api)
            # Permitimos tests y archivos de migración
            elif imported_module.startswith("core.") and not (
                imported_module == "core.api" or imported_module.startswith("core.api.")
            ):
                if (
                    "tests" not in Path(file_path).parts
                    and "migrations" not in Path(file_path).parts
                ):
                    # Check against ALLOWED_CORE_IMPORTS whitelist
                    is_allowed = False
                    for allowed_path in ALLOWED_CORE_IMPORTS:
                        if allowed_path.endswith(".*"):
                            if imported_module.startswith(allowed_path[:-2]):
                                is_allowed = True
                                break
                        elif imported_module == allowed_path:
                            is_allowed = True
                            break

                    if not is_allowed:
                        print(
                            f"ERROR: Importación interna de 'core' prohibida en '{file_path}' (línea {line_number}).\n"
                            f"  -> Se detectó la importación de '{imported_module}'.\n"
                            f"  -> Razón: Las apps no deben acoplarse a partes internas del núcleo. Usa el API formal en 'core.api'.\n"
                            f"  -> Ejemplo: `from core.api import AgenciaMixin` en lugar de `from core.models.base import AgenciaMixin`",
                            file=sys.stderr,
                        )
                        illegal_imports_found = True

    if illegal_imports_found:
        return 1  # Salir con código de error para que el commit falle

    print("OK: No se encontraron importaciones ilegales entre dominios.")
    return 0


if __name__ == "__main__":
    # pre-commit pasa los archivos a verificar como argumentos de línea de comandos
    if len(sys.argv) == 1:
        print("Este script está diseñado para ser ejecutado por pre-commit o manualmente.")
        print("Uso:")
        print("  Manual (todo): python scripts/check_domain_imports.py --all")
        print("  Pre-commit:    python scripts/check_domain_imports.py <file1.py> <file2.py> ...")
        sys.exit(0)

    if sys.argv[1] == "--all":
        # Buscar recursivamente todos los archivos .py en la carpeta apps
        import glob

        apps_path = str(Path(__file__).resolve().parent.parent / "apps")
        files = glob.glob(f"{apps_path}/**/*.py", recursive=True)
    else:
        files = sys.argv[1:]

    sys.exit(main(files))

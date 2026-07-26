"""
Script seguro para agregar docstrings en español.
Solo toca archivos que NO tienen docstring en clases/funciones.
NUNCA modifica imports, herencia de clases, firmas de métodos ni lógica.
"""

import ast
import os
import sys


def needs_docstring(node):
    """True si el nodo no tiene docstring."""
    return not (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    )


def get_simple_doc(node):
    """Genera un docstring corto en español según el tipo de nodo."""
    name = node.name
    if isinstance(node, ast.ClassDef):
        if name in ("Meta", "Media", "Admin", "Router", "Config", "AppConfig"):
            return None
        # Check decorators for common patterns
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id in ("property", "staticmethod", "classmethod"):
                return None
        return f"{name}."
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Skip dunder methods
        if (
            name.startswith("__")
            and name.endswith("__")
            and name not in ("__init__", "__str__", "__repr__")
        ):
            return None
        # Skip decorated methods
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id in ("property", "staticmethod", "classmethod"):
                return None
        return f"{name}."
    return None


def find_sig_end(lines, start_lineno):
    """Encuentra la línea donde termina la firma def/class (contempla saltos de línea en args)."""
    depth = 0
    in_f_string = False
    for i in range(start_lineno, len(lines)):
        line = lines[i]
        # Track f-string depth
        for c in line:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
        # If parens balanced and line has sig end
        if depth <= 0 and ":" in line:
            # Make sure it's not a slice or dict literal
            stripped = line.strip()
            if stripped.endswith(":") or "):" in stripped or "->" in stripped:
                return i
    return start_lineno


def add_docstrings_to_file(filepath):
    """Agrega docstrings faltantes a un archivo Python."""
    with open(filepath, encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    lines = source.split("\n")
    modifications = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if not needs_docstring(node):
            continue

        doc = get_simple_doc(node)
        if doc is None:
            continue

        indent = " " * node.col_offset + "    "
        sig_end = find_sig_end(lines, node.lineno - 1)

        # Skip if there's body content after `:` on the sig line (e.g. `def foo(): ...`)
        after_colon = lines[sig_end].rsplit(":", 1)[-1].strip()
        if after_colon:
            continue

        modifications.append((sig_end, f'{indent}"""{doc}"""'))

    if not modifications:
        return False

    # Apply from bottom up to preserve line numbers
    modifications.sort(key=lambda x: x[0], reverse=True)
    for lineno, text in modifications:
        lines.insert(lineno + 1, text)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return True


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/app"

    if os.path.isfile(root):
        if add_docstrings_to_file(root):
            print(f"  + {root}")
            print("\nModificado: 1 archivo")
        return

    skip_dirs = {
        "migrations",
        "__pycache__",
        ".git",
        ".venv",
        "env",
        "venv",
        "node_modules",
        "static",
        "staticfiles",
        "media",
    }
    modified = 0
    total = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
        if "/migrations/" in dirpath or "/tests/" in dirpath:
            continue
        for fn in filenames:
            if not fn.endswith(".py") or fn.startswith("__"):
                continue
            fpath = os.path.join(dirpath, fn)
            if add_docstrings_to_file(fpath):
                rel = os.path.relpath(fpath, root)
                print(f"  + {rel}")
                modified += 1
            total += 1

    print(f"\nModificados: {modified} / {total} archivos")


if __name__ == "__main__":
    main()

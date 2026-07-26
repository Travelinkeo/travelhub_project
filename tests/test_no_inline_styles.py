import os
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "core" / "templates" / "core"


def list_html_files(base: Path):
    """list_html_files."""
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".html"):
                yield Path(root) / f


def test_no_dangerous_inline_event_handlers():
    """
    Verifica que las plantillas no contengan manejadores de eventos inline
    peligrosos típicos de XSS (como onload=, onerror=) en texto plano,
    promoviendo el uso de Alpine.js (x-on:) o event listeners registrados en JS.
    """
    violations = []
    dangerous_patterns = ["onload=", "onerror="]

    for html_file in list_html_files(TEMPLATES_ROOT):
        content = html_file.read_text(encoding="utf-8", errors="ignore").lower()

        # Eliminar del escaneo los fallbacks seguros de imagen y estilo
        content_clean = content
        content_clean = content_clean.replace('onerror="this.src=', "")
        content_clean = content_clean.replace("onerror='this.src=", "")
        content_clean = content_clean.replace('onerror="this.onerror=null; this.src=', "")
        content_clean = content_clean.replace("onerror='this.onerror=null; this.src=", "")
        content_clean = content_clean.replace('onerror="this.style.display=', "")
        content_clean = content_clean.replace("onerror='this.style.display=", "")

        for pattern in dangerous_patterns:
            if pattern in content_clean:
                violations.append(f"{html_file.name} ({pattern})")

    assert not violations, f"Se encontraron posibles manejadores inline peligrosos en: {violations}"

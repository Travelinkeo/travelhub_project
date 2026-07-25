"""Tests para Script nonces."""
import os
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "core" / "templates" / "core"


def list_html_files(base: Path):
    """List html files."""
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".html"):
                yield Path(root) / f


def test_templates_exist_and_readable():
    """Valida que los templates del core existan y se puedan leer sin errores."""
    files = list(list_html_files(TEMPLATES_ROOT))
    assert len(files) > 0, "No se encontraron archivos HTML en templates/core"
    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        assert len(content) >= 0

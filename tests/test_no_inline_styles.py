import os
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / 'core' / 'templates' / 'core'

def list_html_files(base: Path):
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith('.html'):
                yield Path(root) / f

def test_no_inline_style_attributes():
    violations = []
    for html_file in list_html_files(TEMPLATES_ROOT):
        content = html_file.read_text(encoding='utf-8', errors='ignore')
        if 'style=' in content:
            violations.append(str(html_file.relative_to(TEMPLATES_ROOT.parent)))
    assert not violations, f"Inline style= attributes found in: {violations}"

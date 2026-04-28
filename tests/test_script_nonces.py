import os
import re
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / 'core' / 'templates' / 'core'
SCRIPT_TAG_RE = re.compile(r"<script(?![^>]*\bsrc=)([^>]*?)>", re.IGNORECASE)

def list_html_files(base: Path):
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith('.html'):
                yield Path(root) / f

def test_inline_scripts_have_nonce():
    violations = []
    for html_file in list_html_files(TEMPLATES_ROOT):
        content = html_file.read_text(encoding='utf-8', errors='ignore')
        for match in SCRIPT_TAG_RE.finditer(content):
            attrs = match.group(1)
            # Ignore Django template blocks that may start scripts in extended templates via blocks (handled at runtime)
            if '{%' in attrs or '{{' in attrs:
                continue
            if 'nonce=' not in attrs:
                violations.append(str(html_file.relative_to(TEMPLATES_ROOT.parent)))
    assert not violations, f"Inline <script> tags without nonce found in: {violations}"

"""
Tests de seguridad para validar sanitización XSS, protección SSRF
y validaciones de inputs (Fase 3.4).
"""

import pytest

from core.validators import sanitize_html


@pytest.mark.django_db
class TestSanitizacionXSS:
    """Tests para sanitización HTML contra XSS"""

    def test_sanitize_html_removes_script_tags(self):
        """Debe eliminar tags <script> pero el contenido puede quedar como texto"""
        malicious = "<script>alert('XSS')</script><p>Safe</p>"
        cleaned = sanitize_html(malicious)
        # bleach elimina el tag <script> pero puede dejar el contenido como texto
        assert "<script>" not in cleaned
        assert "</script>" not in cleaned
        assert "<p>Safe</p>" in cleaned

    def test_sanitize_html_removes_onclick_handlers(self):
        """Debe eliminar atributos on* como onclick, onload"""
        malicious = '<p onclick="alert(1)">Click me</p>'
        cleaned = sanitize_html(malicious)
        assert "onclick" not in cleaned
        assert "<p>Click me</p>" in cleaned

    def test_sanitize_html_allows_safe_tags(self):
        """Debe permitir tags seguros como <strong>, <em>, <p>"""
        safe = "<p>Texto <strong>negrita</strong> y <em>cursiva</em></p>"
        cleaned = sanitize_html(safe)
        assert "<strong>negrita</strong>" in cleaned
        assert "<em>cursiva</em>" in cleaned

    def test_sanitize_html_removes_javascript_in_href(self):
        """Debe eliminar javascript: en href"""
        malicious = '<a href="javascript:alert(1)">Click</a>'
        cleaned = sanitize_html(malicious)
        assert "javascript:" not in cleaned

    def test_sanitize_html_allows_safe_links(self):
        """Debe permitir enlaces https seguros"""
        safe = '<a href="https://example.com">Link seguro</a>'
        cleaned = sanitize_html(safe)
        assert 'href="https://example.com"' in cleaned

    def test_sanitize_html_empty_string(self):
        """Debe manejar strings vacíos"""
        assert sanitize_html("") == ""
        # None puede retornar None o "" dependiendo de la implementación
        result = sanitize_html(None)
        assert result == "" or result is None or sanitize_html(None) is None


@pytest.mark.django_db
class TestValidacionInstanceName:
    """Tests para validación de instance_name contra SSRF"""

    def test_instance_name_valid(self):
        """Nombres válidos deben pasar"""
        from core.views.evolution_proxy_views import INSTANCE_NAME_PATTERN

        assert INSTANCE_NAME_PATTERN.match("agencia-test")
        assert INSTANCE_NAME_PATTERN.match("agencia_123")
        assert INSTANCE_NAME_PATTERN.match("TestAgency")
        assert INSTANCE_NAME_PATTERN.match("123")

    def test_instance_name_invalid_ssrF(self):
        """Nombres con caracteres peligrosos deben ser rechazados"""
        from core.views.evolution_proxy_views import INSTANCE_NAME_PATTERN

        assert not INSTANCE_NAME_PATTERN.match("../../etc/passwd")
        assert not INSTANCE_NAME_PATTERN.match("agencia/test")
        assert not INSTANCE_NAME_PATTERN.match("agencia?param=value")
        assert not INSTANCE_NAME_PATTERN.match("agencia#fragment")
        assert not INSTANCE_NAME_PATTERN.match("agencia<script>")


@pytest.mark.django_db
class TestValidacionArchivos:
    """Tests para validación de archivos subidos"""

    def test_filename_sanitization(self):
        """Nombres de archivo deben ser sanitizados"""
        from core.validators import _sanitize_filename

        assert _sanitize_filename("../../etc/passwd") == "passwd"
        assert _sanitize_filename("file with spaces.txt") == "file_with_spaces.txt"
        assert _sanitize_filename("normal-file.pdf") == "normal-file.pdf"

    def test_filename_too_long(self):
        """Nombres largos deben ser truncados"""
        from core.validators import _sanitize_filename

        long_name = "a" * 300 + ".pdf"
        sanitized = _sanitize_filename(long_name)
        assert len(sanitized) <= 200

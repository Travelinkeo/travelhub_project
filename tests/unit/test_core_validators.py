"""Tests para core/validators.py — validadores de archivos y campos."""

import pytest
from django.core.exceptions import ValidationError

pytestmark = [pytest.mark.unit]


class TestValidateFileExtension:
    @pytest.fixture(autouse=True)
    def _setup(self, settings):
        settings.VALID_IMAGE_EXTENSIONS = [".jpg", ".png"]
        settings.VALID_DOCUMENT_EXTENSIONS = [".pdf"]

    def test_valid_extension(self):
        from core.validators import validate_file_extension

        validate_file_extension("image.jpg", "image")

    def test_invalid_extension(self):
        from core.validators import validate_file_extension

        with pytest.raises(ValidationError):
            validate_file_extension("file.exe", "image")

    def test_valid_document(self):
        from core.validators import validate_file_extension

        validate_file_extension("doc.pdf", "document")


class TestValidateNoVacio:
    def test_valid_string(self):
        from core.validators import validar_no_vacio_o_espacios

        validar_no_vacio_o_espacios("hello")

    def test_empty_string_raises(self):
        from core.validators import validar_no_vacio_o_espacios

        with pytest.raises(ValidationError):
            validar_no_vacio_o_espacios("")

    def test_whitespace_only_raises(self):
        from core.validators import validar_no_vacio_o_espacios

        with pytest.raises(ValidationError):
            validar_no_vacio_o_espacios("   ")

    def test_none_raises(self):
        from core.validators import validar_no_vacio_o_espacios

        with pytest.raises(ValidationError):
            validar_no_vacio_o_espacios(None)

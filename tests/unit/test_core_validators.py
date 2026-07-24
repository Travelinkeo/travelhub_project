import io

import pytest
from django.core.exceptions import ValidationError

pytestmark = [pytest.mark.unit]


class TestValidateFileExtension:
    def test_valid_extension(self):
        from core.validators import validate_file_extension

        f = io.BytesIO(b"\xff\xd8\xff")
        f.name = "image.jpg"
        validate_file_extension(f)

    def test_invalid_extension(self):
        from core.validators import validate_file_extension

        f = io.BytesIO(b"some data")
        f.name = "file.exe"
        with pytest.raises(ValidationError):
            validate_file_extension(f)

    def test_valid_document(self):
        from core.validators import validate_file_extension

        f = io.BytesIO(b"%PDF-1.4")
        f.name = "doc.pdf"
        validate_file_extension(f)

    def test_emoji_file_is_invalid(self):
        from core.validators import validate_file_extension

        f = io.BytesIO(b"some data")
        f.name = "file.gif"
        with pytest.raises(ValidationError):
            validate_file_extension(f)


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

    def test_none_passes(self):
        from core.validators import validar_no_vacio_o_espacios

        validar_no_vacio_o_espacios(None)

    def test_number_passes(self):
        from core.validators import validar_no_vacio_o_espacios

        validar_no_vacio_o_espacios(0)

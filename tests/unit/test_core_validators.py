"""Tests para Core validators (Unit)."""
import io

import pytest
from django.core.exceptions import ValidationError

pytestmark = [pytest.mark.unit]


class TestValidateFileExtension:
    """Test Validate File Extension."""
    def test_valid_extension(self):
        """Valid extension."""
        from core.validators import validate_file_extension

        f = io.BytesIO(b"\xff\xd8\xff")
        f.name = "image.jpg"
        validate_file_extension(f)

    def test_invalid_extension(self):
        """Invalid extension."""
        from core.validators import validate_file_extension

        f = io.BytesIO(b"some data")
        f.name = "file.exe"
        with pytest.raises(ValidationError):
            validate_file_extension(f)

    def test_valid_document(self):
        """Valid document."""
        from core.validators import validate_file_extension

        f = io.BytesIO(b"%PDF-1.4")
        f.name = "doc.pdf"
        validate_file_extension(f)

    def test_emoji_file_is_invalid(self):
        """Emoji file is invalid."""
        from core.validators import validate_file_extension

        f = io.BytesIO(b"some data")
        f.name = "file.gif"
        with pytest.raises(ValidationError):
            validate_file_extension(f)


class TestValidateNoVacio:
    """Test Validate No Vacio."""
    def test_valid_string(self):
        """Valid string."""
        from core.validators import validar_no_vacio_o_espacios

        validar_no_vacio_o_espacios("hello")

    def test_empty_string_raises(self):
        """Empty string raises."""
        from core.validators import validar_no_vacio_o_espacios

        with pytest.raises(ValidationError):
            validar_no_vacio_o_espacios("")

    def test_whitespace_only_raises(self):
        """Whitespace only raises."""
        from core.validators import validar_no_vacio_o_espacios

        with pytest.raises(ValidationError):
            validar_no_vacio_o_espacios("   ")

    def test_none_passes(self):
        """None passes."""
        from core.validators import validar_no_vacio_o_espacios

        validar_no_vacio_o_espacios(None)

    def test_number_passes(self):
        """Number passes."""
        from core.validators import validar_no_vacio_o_espacios

        validar_no_vacio_o_espacios(0)

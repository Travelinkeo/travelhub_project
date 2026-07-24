"""Tests para core/fields.py — EncryptedCharField y EncryptedTextField."""

import pytest
from django.core.exceptions import ImproperlyConfigured

pytestmark = [pytest.mark.unit]


class TestEncryptedCharField:
    def test_multiplies_max_length(self):
        from core.fields import EncryptedCharField

        field = EncryptedCharField(max_length=100)
        assert field.max_length == 400

    def test_deconstruct_restores_max_length(self):
        from core.fields import EncryptedCharField

        field = EncryptedCharField(max_length=100)
        name, path, args, kwargs = field.deconstruct()
        assert kwargs["max_length"] == 100

    def test_encrypt_decrypt_roundtrip(self, monkeypatch, settings):
        settings.ENCRYPTION_KEY = "test-key-must-be-32-bytes-long-here!!"

        from core.fields import EncryptedCharField

        field = EncryptedCharField(max_length=100)

        encrypted = field._encrypt("secret-value")
        assert encrypted.startswith("gAAAAA")
        assert encrypted != "secret-value"

        decrypted = field._decrypt(encrypted)
        assert decrypted == "secret-value"

    def test_encrypt_already_encrypted(self, monkeypatch, settings):
        settings.ENCRYPTION_KEY = "test-key-must-be-32-bytes-long-here!!"

        from core.fields import EncryptedCharField

        field = EncryptedCharField(max_length=100)
        encrypted = field._encrypt("value")
        double_encrypted = field._encrypt(encrypted)
        assert double_encrypted == encrypted

    def test_raises_error_without_key(self):
        from core.fields import EncryptedCharField

        field = EncryptedCharField(max_length=100)
        with pytest.raises(ImproperlyConfigured):
            field._encrypt("test")

    def test_get_prep_value_none(self, settings):
        settings.ENCRYPTION_KEY = "test-key-must-be-32-bytes-long-here!!"

        from core.fields import EncryptedCharField

        field = EncryptedCharField(max_length=100)
        assert field.get_prep_value(None) is None
        assert field.get_prep_value("") == ""

    def test_from_db_value_none(self, settings):
        settings.ENCRYPTION_KEY = "test-key-must-be-32-bytes-long-here!!"

        from core.fields import EncryptedCharField

        field = EncryptedCharField(max_length=100)
        assert field.from_db_value(None, None, None) is None
        assert field.from_db_value("", None, None) == ""

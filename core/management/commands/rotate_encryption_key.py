"""
Management command to rotate the ENCRYPTION_KEY.

Usage:
    # 1. Generate a new key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # 2. Run the rotation:
    python manage.py rotate_encryption_key --new-key="<base64-urlsafe-32byte-key>"

    # 3. Update ENCRYPTION_KEY in .env with the new key

    # 4. Restart all Django processes

Algorithm:
    1. Discovers all EncryptedCharField/EncryptedTextField in all models.
    2. For each field: reads the plaintext (decrypts with current
       settings.ENCRYPTION_KEY), then re-encrypts with --new-key.
    3. Writes the new ciphertext back to the database column directly.
"""

import logging
from collections import defaultdict

from cryptography.fernet import Fernet
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core.fields import EncryptedCharField, EncryptedTextField

logger = logging.getLogger(__name__)


def _discover_encrypted_fields():
    """Returns dict: {model: [(field_name, field_instance), ...]}"""
    results = defaultdict(list)
    for config in apps.get_app_configs():
        for model in config.get_models():
            for field in model._meta.fields:
                if isinstance(field, EncryptedCharField | EncryptedTextField):
                    results[model].append((field.column, field))
    return dict(results)


class Command(BaseCommand):
    """Command."""

    help = "Re-encrypts all EncryptedCharField/TextField values with a new ENCRYPTION_KEY"

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument(
            "--new-key",
            required=True,
            help="New Fernet key (base64-urlsafe-32byte). Generated with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be done, without modifying data",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to process per batch (default: 1000)",
        )

    def handle(self, *args, **options):
        """handle."""
        new_key = options["new_key"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        # Validate new key
        try:
            new_fernet = Fernet(new_key.encode())
        except Exception as e:
            raise CommandError(f"Invalid --new-key: {e}") from e

        from django.conf import settings

        old_key = getattr(settings, "ENCRYPTION_KEY", None)
        if not old_key:
            raise CommandError("ENCRYPTION_KEY is not set in settings")
        try:
            old_fernet = Fernet(old_key.encode())
        except Exception as e:
            raise CommandError(f"Current ENCRYPTION_KEY is invalid: {e}") from e

        encrypted_fields = _discover_encrypted_fields()
        if not encrypted_fields:
            self.stdout.write(self.style.WARNING("No encrypted fields found in any model."))
            return

        self.stdout.write(f"Using old key: {old_key[:16]}...{old_key[-8:]}")
        self.stdout.write(f"Using new key: {new_key[:16]}...{new_key[-8:]}")
        self.stdout.write("")

        total_models = 0
        total_rows = 0
        total_fields = 0

        for model, fields in encrypted_fields.items():
            table = model._meta.db_table
            pk_col = model._meta.pk.column
            rows_count = model.objects.count()
            if rows_count == 0:
                continue

            total_models += 1
            total_rows += rows_count
            total_fields += len(fields)

            self.stdout.write(
                f"[{table}] {model.__name__}: {rows_count} rows x {len(fields)} fields"
            )

            if dry_run:
                continue

            processed = 0
            for offset in range(0, rows_count, batch_size):
                batch = model.objects.all()[offset : offset + batch_size]
                updates = []
                for instance in batch:
                    row_updates = {}
                    for field_name, _field_obj in fields:
                        raw_value = getattr(instance, field_name)
                        if raw_value is None or raw_value == "":
                            continue
                        try:
                            plaintext = old_fernet.decrypt(raw_value.encode()).decode("utf-8")
                            new_cipher = new_fernet.encrypt(plaintext.encode()).decode("utf-8")
                            row_updates[field_name] = new_cipher
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  ERROR: {table}.{field_name} pk={getattr(instance, pk_col)}: {e}"
                                )
                            )
                            continue
                    if row_updates:
                        updates.append((getattr(instance, pk_col), row_updates))

                # Apply updates for this batch via raw SQL
                if updates:
                    with transaction.atomic():
                        with connection.cursor() as cur:
                            for pk_val, row_updates in updates:
                                set_clause = ", ".join(f"{col} = %s" for col in row_updates)
                                sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = %s"  # noqa: S608
                                params = list(row_updates.values()) + [pk_val]
                                cur.execute(sql, params)

                processed += len(batch)
                self.stdout.write(f"  Processed {processed}/{rows_count} rows", ending="\r")

            self.stdout.write(f"  Done. {processed} rows processed.")
            self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            self.style.SUCCESS(
                f"Rotation complete: {total_models} models, {total_rows} rows, {total_fields} fields."
            )
        )
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "NEXT STEP: Update ENCRYPTION_KEY in .env with the new key and restart all Django processes."
            )
        )

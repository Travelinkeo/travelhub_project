import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command."""

    help = "Realiza backup de la base de datos PostgreSQL, lo cifra con GPG y sube a R2"

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument(
            "--retention-days",
            type=int,
            default=30,
            help="Días de retención de backups en R2 (default: 30)",
        )

    def handle(self, *args, **options):
        """handle."""
        retention_days = options["retention_days"]
        db_url = os.environ.get("DATABASE_URL", "")

        if not db_url:
            self.stderr.write(self.style.ERROR("DATABASE_URL no configurada"))
            return

        try:
            from urllib.parse import urlparse

            parsed = urlparse(db_url)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"travelhub_backup_{timestamp}.sql.gz.gpg"
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, f"travelhub_backup_{timestamp}.sql.gz")
            final_path = os.path.join(temp_dir, filename)

            env = os.environ.copy()
            if parsed.password:
                env["PGPASSWORD"] = parsed.password

            cmd = [
                "pg_dump",
                "-h",
                parsed.hostname or "localhost",
                "-p",
                str(parsed.port or 5432),
                "-U",
                parsed.username or "postgres",
                "-d",
                parsed.path.lstrip("/") or "travelhub",
                "--no-owner",
                "--no-acl",
            ]

            self.stdout.write(f"Iniciando backup: {filename}")

            with open(temp_path, "wb") as f:
                pg_dump = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env)  # noqa: S603
                gzip_proc = subprocess.Popen(  # noqa: S603
                    ["gzip", "-c"],  # noqa: S607
                    stdin=pg_dump.stdout,
                    stdout=f,
                )
                pg_dump.stdout.close()
                gzip_proc.communicate()

                if pg_dump.returncode != 0:
                    self.stderr.write(
                        self.style.ERROR(f"pg_dump falló con código {pg_dump.returncode}")
                    )
                    return

            # Cifrar con GPG
            gpg_recipient = getattr(settings, "BACKUP_GPG_RECIPIENT", None)
            if not gpg_recipient:
                self.stderr.write(
                    self.style.ERROR("BACKUP_GPG_RECIPIENT no configurado en settings")
                )
                return

            self.stdout.write("Cifrando backup con GPG...")
            gpg_cmd = [
                "gpg",
                "--trust-model",
                "always",
                "--encrypt",
                "--recipient",
                gpg_recipient,
                "--output",
                final_path,
                temp_path,
            ]
            gpg_result = subprocess.run(gpg_cmd, capture_output=True, text=True)  # noqa: S603
            if gpg_result.returncode != 0:
                self.stderr.write(self.style.ERROR(f"GPG falló: {gpg_result.stderr}"))
                return

            # Subir a R2
            self._upload_to_r2(final_path, filename)

            file_size_mb = os.path.getsize(final_path) / (1024 * 1024)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backup completado y subido: {filename} ({file_size_mb:.1f} MB)"
                )
            )

            # Limpieza local (solo temp)
            os.remove(temp_path)
            os.remove(final_path)
            os.rmdir(temp_dir)

            # Limpiar R2 antiguos
            self._cleanup_old_r2_backups(retention_days)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error en backup: {e}"))
            logger.error(f"Backup failed: {e}")

    def _upload_to_r2(self, filepath, filename):
        """Sube el archivo cifrado a Cloudflare R2."""
        try:
            import boto3
            from botocore.config import Config

            r2_endpoint = getattr(settings, "R2_ENDPOINT_URL", None)
            r2_access_key = getattr(settings, "R2_ACCESS_KEY_ID", None)
            r2_secret_key = getattr(settings, "R2_SECRET_ACCESS_KEY", None)
            r2_bucket = getattr(settings, "R2_BUCKET_NAME", None)

            if not all([r2_endpoint, r2_access_key, r2_secret_key, r2_bucket]):
                self.stderr.write(self.style.ERROR("Configuración R2 incompleta en settings"))
                return

            s3 = boto3.client(
                "s3",
                endpoint_url=r2_endpoint,
                aws_access_key_id=r2_access_key,
                aws_secret_access_key=r2_secret_key,
                config=Config(signature_version="s3v4"),
            )

            self.stdout.write(f"Subiendo a R2: {filename}...")
            s3.upload_file(filepath, r2_bucket, f"backups/{filename}")
            self.stdout.write(self.style.SUCCESS("Subida a R2 completada"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error subiendo a R2: {e}"))
            raise

    def _cleanup_old_r2_backups(self, retention_days):
        """Elimina backups antiguos de R2 (retención 30 días)."""
        try:
            import boto3
            from botocore.config import Config

            r2_endpoint = getattr(settings, "R2_ENDPOINT_URL", None)
            r2_access_key = getattr(settings, "R2_ACCESS_KEY_ID", None)
            r2_secret_key = getattr(settings, "R2_SECRET_ACCESS_KEY", None)
            r2_bucket = getattr(settings, "R2_BUCKET_NAME", None)

            if not all([r2_endpoint, r2_access_key, r2_secret_key, r2_bucket]):
                return

            s3 = boto3.client(
                "s3",
                endpoint_url=r2_endpoint,
                aws_access_key_id=r2_access_key,
                aws_secret_access_key=r2_secret_key,
                config=Config(signature_version="s3v4"),
            )

            cutoff = datetime.now() - timedelta(days=retention_days)
            paginator = s3.get_paginator("list_objects_v2")
            deleted = 0

            for page in paginator.paginate(Bucket=r2_bucket, Prefix="backups/"):
                for obj in page.get("Contents", []):
                    if obj["LastModified"].replace(tzinfo=None) < cutoff:
                        s3.delete_object(Bucket=r2_bucket, Key=obj["Key"])
                        deleted += 1
                        self.stdout.write(f"  Eliminado backup antiguo de R2: {obj['Key']}")

            if deleted:
                self.stdout.write(f"Rotación R2 completada: {deleted} backups eliminados")

        except Exception as e:
            logger.warning(f"Error limpiando R2: {e}")

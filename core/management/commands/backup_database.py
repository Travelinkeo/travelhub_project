import logging
import os
import subprocess
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Realiza backup de la base de datos PostgreSQL y rota backups antiguos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            type=int,
            default=7,
            help="Días de retención de backups locales (default: 7)",
        )

    def handle(self, *args, **options):
        retention_days = options["retention_days"]
        db_url = os.environ.get("DATABASE_URL", "")

        if not db_url:
            self.stderr.write(self.style.ERROR("DATABASE_URL no configurada"))
            return

        try:
            from urllib.parse import urlparse

            parsed = urlparse(db_url)

            backup_dir = os.path.join(settings.BASE_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"travelhub_backup_{timestamp}.sql.gz"
            filepath = os.path.join(backup_dir, filename)

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

            with open(filepath, "wb") as f:
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
                    os.remove(filepath)
                    return

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            self.stdout.write(
                self.style.SUCCESS(f"Backup completado: {filename} ({file_size_mb:.1f} MB)")
            )

            self._cleanup_old_backups(backup_dir, retention_days)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error en backup: {e}"))
            logger.error(f"Backup failed: {e}")

    def _cleanup_old_backups(self, backup_dir, retention_days):
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0

        for filename in os.listdir(backup_dir):
            if not filename.startswith("travelhub_backup_") or not filename.endswith(".sql.gz"):
                continue

            filepath = os.path.join(backup_dir, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

            if file_mtime < cutoff:
                os.remove(filepath)
                deleted += 1
                self.stdout.write(f"  Eliminado backup antiguo: {filename}")

        if deleted:
            self.stdout.write(f"Rotación completada: {deleted} backups eliminados")
        else:
            self.stdout.write("No hay backups para rotar")

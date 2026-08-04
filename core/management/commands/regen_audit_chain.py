"""Regenera la cadena de hashes de AuditLog (repara registros históricos)."""

import hashlib
import json

from django.core.management.base import BaseCommand

from core.api import AuditLog


def _canon(log) -> str:
    """Construye el canon EXACTO que usa AuditLog.save() y verify_audit_chain()."""
    payload = {
        "modelo": log.modelo,
        "object_id": log.object_id,
        "accion": log.accion,
        "descripcion": log.descripcion or "",
        "datos_previos": log.datos_previos,
        "datos_nuevos": log.datos_nuevos,
        "metadata_extra": log.metadata_extra,
        "creado": log.creado.isoformat(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Command(BaseCommand):
    """Regenera la cadena de hashes de AuditLog."""

    help = (
        "Regenera previous_hash/record_hash de TODOS los AuditLog en orden de creación. "
        "Útil tras el fix de auto_now_add→default (los hashes históricos quedaron "
        "anclados a un timestamp que nunca se guardó). Requiere: python manage.py "
        "regen_audit_chain"
    )

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo calcula y reporta cuántos registros se corregirían, sin escribir.",
        )

    def handle(self, *args, **options):
        """handle."""
        dry_run = options["dry_run"]
        qs = AuditLog.objects.all().order_by("creado", "id_audit_log")
        total = qs.count()
        self.stdout.write(f"AuditLog totales: {total}")

        prev_hash: str | None = None
        corregidos = 0
        cambios = []

        for log in qs.iterator():
            nuevo_prev = prev_hash if prev_hash else "0" * 64
            canon = _canon(log)
            base = nuevo_prev + "|" + canon
            nuevo_hash = hashlib.sha256(base.encode("utf-8")).hexdigest()

            if log.previous_hash != nuevo_prev or log.record_hash != nuevo_hash:
                cambios.append(
                    (log.id_audit_log, log.previous_hash, nuevo_prev, log.record_hash, nuevo_hash)
                )
                corregidos += 1
                if not dry_run:
                    AuditLog.objects.filter(pk=log.pk).update(
                        previous_hash=nuevo_prev, record_hash=nuevo_hash
                    )
            prev_hash = nuevo_hash

        self.stdout.write(f"Registros a corregir: {corregidos}")
        if dry_run and corregidos:
            self.stdout.write("Primeros 5 cambios (dry-run, no aplicados):")
            for cid, old_prev, new_prev, old_hash, new_hash in cambios[:5]:
                self.stdout.write(
                    f"  id={cid}: prev {old_prev[:12]}→{new_prev[:12]} hash {old_hash[:12]}→{new_hash[:12]}"
                )
        if not dry_run and corregidos:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Cadena regenerada ({corregidos} corregidos).")
            )
        elif not dry_run:
            self.stdout.write(self.style.SUCCESS("✅ Cadena ya era válida, 0 cambios."))

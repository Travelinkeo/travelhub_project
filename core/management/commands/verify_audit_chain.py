from django.core.management.base import BaseCommand

from core.utils import verify_audit_chain


class Command(BaseCommand):
    help = 'Verifica la integridad de la cadena de hashes de AuditLog.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, help='Limitar la verificación a los N registros más antiguos (para pruebas rápidas).')

    def handle(self, *args, **options):
        limit = options.get('limit')
        ok, break_id, reason = verify_audit_chain(limit=limit)
        if ok:
            self.stdout.write(self.style.SUCCESS('AuditLog hash chain OK'))
        else:
            if break_id:
                self.stdout.write(self.style.ERROR(f'RUPTURA en AuditLog id={break_id}: {reason}'))
            else:
                self.stdout.write(self.style.ERROR(f'Error verificando cadena: {reason}'))
            # BaseCommand no provee exit(); usamos SystemExit para señalizar fallo (código 1)
            raise SystemExit(1)

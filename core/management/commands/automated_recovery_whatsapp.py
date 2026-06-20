from django.core.management.base import BaseCommand

from apps.automation.services.collection_ai_service import CollectionAIService


class Command(BaseCommand):
    help = "Detecta facturas vencidas y envía recordatorios personalizados vía WhatsApp con IA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula el proceso sin enviar mensajes reales.",
        )
        parser.add_argument(
            "--agencia-id",
            type=int,
            help="Filtrar por agencia específica (ID).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        agencia_id = options.get("agencia_id")

        self.stdout.write(
            self.style.NOTICE(f"Iniciando proceso de cobranza IA (Dry Run: {dry_run})")
        )

        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            try:
                agencia = Agencia.objects.get(pk=agencia_id)
            except Agencia.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Agencia {agencia_id} no encontrada."))
                return

        service = CollectionAIService(agencia=agencia)
        facturas_vencidas = service.get_pending_portfolio(days_threshold=-1)

        if not facturas_vencidas:
            self.stdout.write(self.style.SUCCESS("No hay facturas vencidas pendientes."))
            return

        self.stdout.write(f"Encontradas {len(facturas_vencidas)} facturas vencidas.")

        if dry_run:
            for factura in facturas_vencidas:
                cliente = factura.cliente
                self.stdout.write(
                    f"  - {factura.numero_factura} | "
                    f"Cliente: {cliente.get_nombre_completo() if cliente else 'N/A'} | "
                    f"Monto: {factura.saldo_pendiente} {factura.moneda.codigo_iso if factura.moneda else ''} | "
                    f"Teléfono: {getattr(cliente, 'telefono_principal', 'N/A') if cliente else 'N/A'}"
                )
        else:
            resultados = service.process_overdue_accounts()
            exitos = sum(1 for r in resultados if r["success"])
            fallos = sum(1 for r in resultados if not r["success"])

            for res in resultados:
                status = (
                    self.style.SUCCESS("ENVIADO") if res["success"] else self.style.ERROR("FALLO")
                )
                self.stdout.write(
                    f"  {res['factura']} -> {status} | Error: {res.get('error', 'Ninguno')}"
                )

            self.stdout.write(
                self.style.SUCCESS(f"\nCompletado: {exitos} enviados, {fallos} fallidos.")
            )

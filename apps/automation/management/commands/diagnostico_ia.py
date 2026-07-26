import time
import traceback

from django.core.management.base import BaseCommand

from apps.automation.services.ticket_parser_service import TicketParserService
from apps.bookings.models import BoletoImportado


class Command(BaseCommand):
    """Command."""

    help = "SRE L3 Forensic Diagnostic tool for ticket parser silent failures."

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument("boleto_id", type=int, help="ID of the BoletoImportado to diagnose.")

    def handle(self, *args, **options):
        """handle."""
        boleto_id = options["boleto_id"]
        # Corregido: Uso de style.WARNING en lugar del inexistente MIGRATE_HEADER
        self.stdout.write(
            self.style.WARNING(
                f"\n🔍 [SRE L3 DIAGNOSTIC] Starting analysis for Boleto ID: {boleto_id}"
            )
        )

        try:
            manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
            boleto = manager.get(pk=boleto_id)
        except BoletoImportado.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Error: Boleto with ID {boleto_id} does not exist in the database."
                )
            )
            return

        # 2. Print initial database state
        self.stdout.write(self.style.WARNING("\n📋 [INITIAL DB STATE]"))
        self.stdout.write(f" - Estado de Parseo: {boleto.estado_parseo}")
        self.stdout.write(
            f" - Archivo asociado: {boleto.archivo_boleto.name if boleto.archivo_boleto else 'None'}"
        )
        self.stdout.write(f" - Log de Parseo: {boleto.log_parseo or 'Sin logs registrados.'}")

        # 🩹 MONKEY PATCH: Inyectamos dinámicamente el atributo 'id' por si el parser lo necesita
        if not hasattr(boleto, "id"):
            boleto.id = boleto.pk
        self.stdout.write(
            f" - ID (Monkey Patch Check): {getattr(boleto, 'id', 'Falta atributo id')}"
        )

        # 3. Execute the safety rewind (rebobinado)
        if boleto.archivo_boleto:
            self.stdout.write(
                self.style.NOTICE("\n⏪ [REWIND] Executing safety rewind on file stream...")
            )
            try:
                if hasattr(boleto.archivo_boleto, "open"):
                    boleto.archivo_boleto.open()
                if hasattr(boleto.archivo_boleto, "seek"):
                    boleto.archivo_boleto.seek(0)
                    self.stdout.write(
                        self.style.SUCCESS(
                            " ✅ Stream rewind completed successfully. Position reset to Byte 0."
                        )
                    )
                else:
                    self.stdout.write(self.style.WARNING(" ⚠️ file object has no seek() method."))
            except Exception as e_stream:
                self.stdout.write(self.style.ERROR(f" ❌ Stream rewind failed: {e_stream}"))
        else:
            self.stdout.write(
                self.style.ERROR(" ❌ Warning: No file associated with this ticket record.")
            )

        # 4. Ingest and timing
        # Corregido: Uso de style.WARNING en lugar de MIGRATE_LABEL
        self.stdout.write(
            self.style.WARNING(
                "\n🚀 [PARSER INGEST] Running TicketParserService().process_boleto(boleto) síncronamente..."
            )
        )

        start_time = time.time()
        success = False
        try:
            parser_service = TicketParserService()
            parser_service.process_boleto(boleto)
            duration = time.time() - start_time
            success = True
        except Exception as e:
            duration = time.time() - start_time
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write("\033[91m🔥 [FATAL PARSER EXCEPTION DETECTED] 🔥\033[0m")
            self.stdout.write(f"\033[91mTime Elapsed until Failure: {duration:.4f} seconds\033[0m")
            self.stdout.write(f"\033[91mException Type: {type(e).__name__}\033[0m")
            self.stdout.write(f"\033[91mException Message: {str(e)}\033[0m\n")

            tb_str = traceback.format_exc()
            self.stdout.write(f"\033[91m{tb_str}\033[0m")
            self.stdout.write("=" * 80 + "\n")

        # 5. Print final database state and timing if successful
        if success:
            boleto.refresh_from_db()
            self.stdout.write(
                self.style.SUCCESS("\n🎉 [DIAGNOSTIC COMPLETED] Execution finished successfully!")
            )
            self.stdout.write(
                self.style.SUCCESS(f" ⏱️ Total execution duration: {duration:.4f} seconds")
            )
            self.stdout.write(self.style.WARNING("\n📋 [FINAL DB STATE]"))
            self.stdout.write(f" - Estado de Parseo: {boleto.estado_parseo}")
            self.stdout.write(f" - Venta Asociada: {boleto.venta_asociada_id or 'None'}")
            self.stdout.write(
                f" - Datos Parseados: {bool(boleto.datos_parseados)} (Campos: {list(boleto.datos_parseados.keys()) if boleto.datos_parseados else 'Vacío'})"
            )
            self.stdout.write(f" - Log de Parseo Final: {boleto.log_parseo or 'Sin logs/Vacío.'}")
            if str(boleto.estado_parseo) in ["ERR", "REV"]:
                self.stdout.write(
                    self.style.ERROR(
                        f" ❌ Processing finished with parsing status: {boleto.estado_parseo}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f" ✅ Processing finished with status: {boleto.estado_parseo}"
                    )
                )

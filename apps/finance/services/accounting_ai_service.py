from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.finance.schemas.accounting_schemas import AsientoContableSchema

logger = logging.getLogger(__name__)


class AccountingAIService:
    """
    SERVICIO DE CONTABILIDAD IA (CPA ENGINE):
    Utiliza el razonamiento de Gemini para generar asientos contables
    basados en descripciones de transacciones o hallazgos de conciliación.
    """

    @classmethod
    @transaction.atomic
    def generar_asiento_con_ia(
        cls, descripcion_transaccion: str, context_details: dict | None = None
    ) -> "AsientoContable | None":
        """
        Interpreta una transacción y crea el asiento contable físico en TravelHub.

        Args:
            descripcion_transaccion: Texto natural describiendo el movimiento.
            context_details: Diccionario opcional con montos, fechas o IDs involucrados.
        """
        logger.info(f"Accounting AI: Generando asiento para: '{descripcion_transaccion[:80]}...'")

        contexto_str = f"\nDATOS TÉCNICOS: {context_details}" if context_details else ""
        full_prompt = f"CONTABILIZA LA SIGUIENTE TRANSACCIÓN:\n{descripcion_transaccion}{contexto_str}"

        try:
            from django.apps import apps
            from django.utils.module_loading import import_string

            ai_engine = import_string("apps.automation.services.ai_engine.ai_engine")
            ACCOUNTING_SYSTEM_PROMPT = import_string(
                "apps.automation.services.prompts.ACCOUNTING_SYSTEM_PROMPT"
            )
            AsientoContable = apps.get_model("contabilidad", "AsientoContable")
            MovimientoContable = apps.get_model("contabilidad", "MovimientoContable")
            CuentaContable = apps.get_model("contabilidad", "CuentaContable")

            datos_asiento = ai_engine.call_gemini(
                prompt=full_prompt,
                response_schema=AsientoContableSchema,
                system_instruction=ACCOUNTING_SYSTEM_PROMPT,
                temperature=0.0,
            )

            if not datos_asiento or not datos_asiento.get("lineas"):
                logger.error("El motor IA devolvió un asiento vacío o sin líneas.")
                return None

            asiento = AsientoContable.objects.create(
                glosa=datos_asiento["glosa"],
                fecha_contable=datos_asiento.get("fecha_contable", timezone.now().date()),
                tipo_asiento=datos_asiento.get("tipo_asiento", AsientoContable.TipoAsiento.DIARIO),
                estado=AsientoContable.EstadoAsiento.BORRADOR,
            )

            for l_schema in datos_asiento["lineas"]:
                cuenta = CuentaContable.objects.filter(
                    codigo=l_schema["codigo_cuenta"]
                ).first()
                if not cuenta:
                    cuenta = CuentaContable.objects.filter(
                        nombre__icontains=l_schema["nombre_cuenta"]
                    ).first()

                if not cuenta:
                    error_msg = (
                        f"No se pudo localizar la cuenta contable: "
                        f"{l_schema['codigo_cuenta']} - {l_schema['nombre_cuenta']}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                MovimientoContable.objects.create(
                    asiento=asiento,
                    cuenta=cuenta,
                    tipo=l_schema["tipo"],
                    monto_ves=Decimal(str(round(l_schema["monto_ves"], 2))),
                    monto_usd=Decimal(str(round(l_schema["monto_usd"], 2))),
                )

            logger.info(f"Asiento Contable {asiento.pk} creado exitosamente por CPA Engine.")
            return asiento

        except Exception:
            logger.exception("Fallo crítico en el motor de contabilidad IA")
            return None

"""
apps/automation/services/ticket_review_service.py
==================================================
Fase 3 — Refactorización de Fat Views.

Responsabilidad única: Encapsula toda la lógica de negocio del
'AI Studio' de revisión de boletos, que antes vivía en
`ReviewBoletoView.post` de `core/views/upload.py`.

La vista queda reducida a: leer request → llamar servicio → devolver HTTP response.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from apps.automation.services.ticket_parser_service import TicketParserService
from apps.bookings.models import BoletoImportado, Venta

logger = logging.getLogger(__name__)


@dataclass
class StudioFormData:
    """
    Datos tipados del formulario del AI Studio.
    Desacopla el parseo de request.POST del servicio.
    """

    nombre: str | None
    foid: str | None
    cliente_id: str | None
    pnr: str | None
    pnr_aerolinea: str | None
    ticket_no: str | None
    fare: str
    taxes: str
    total: str
    total_currency: str

    @classmethod
    def from_post(cls, post_data) -> "StudioFormData":
        """Extrae y normaliza los datos del request.POST."""
        return cls(
            nombre=post_data.get("nombre_pasajero") or None,
            foid=post_data.get("foid_pasajero") or None,
            cliente_id=post_data.get("cliente_id") or None,
            pnr=post_data.get("localizador_pnr") or None,
            pnr_aerolinea=post_data.get("pnr_aerolinea") or None,
            ticket_no=post_data.get("ticket_number") or None,
            fare=post_data.get("fare_amount", "0"),
            taxes=post_data.get("taxes_amount", "0"),
            total=post_data.get("total_amount", "0"),
            total_currency=post_data.get("total_currency", "USD"),
        )


@dataclass
class ReviewResult:
    """Resultado de la operación de revisión. Desacopla el servicio de Django HTTP."""

    success: bool
    venta: Venta | None = None
    error_message: str | None = None


class TicketReviewService:
    """
    Orquesta la actualización manual de un boleto desde el AI Studio
    y su reprocesamiento hacia una Venta.

    Flujo:
    1. Actualizar campos directos del BoletoImportado desde el formulario.
    2. Sincronizar datos_parseados (para el VentaBuilder).
    3. Delegar el reprocesamiento a TicketParserService (manual_only=True).
    4. Devolver un ReviewResult tipado.
    """

    def apply_and_reprocess(
        self,
        boleto: BoletoImportado,
        form_data: StudioFormData,
        session: dict,
    ) -> ReviewResult:
        """
        Punto de entrada principal. Aplica los cambios del formulario
        al boleto y lanza el reprocesamiento sin re-correr la IA.

        Args:
            boleto: La instancia de BoletoImportado a actualizar.
            form_data: Datos ya parseados del formulario.
            session: django request.session (para persistir forced_cliente_id).

        Returns:
            ReviewResult con la Venta resultante o el mensaje de error.
        """
        self._update_model_fields(boleto, form_data)
        self._sync_parsed_data(boleto, form_data)
        self._append_audit_log(boleto)
        boleto.save()

        # Persistir la asociación de cliente en sesión (usada por VentaBuilder)
        if form_data.cliente_id:
            session["forced_cliente_id"] = form_data.cliente_id

        return self._reprocess(boleto, form_data.cliente_id)

    # ─── Pasos internos ──────────────────────────────────────────────────────

    def _update_model_fields(self, boleto: BoletoImportado, fd: StudioFormData) -> None:
        """Actualiza los campos ORM del boleto con los valores del formulario."""
        if fd.foid:
            boleto.foid_pasajero = fd.foid
        if fd.nombre:
            boleto.nombre_pasajero_procesado = fd.nombre
            boleto.nombre_pasajero_completo = fd.nombre
        if fd.pnr:
            boleto.localizador_pnr = fd.pnr
        if fd.ticket_no:
            boleto.numero_boleto = fd.ticket_no

        self._update_amounts(boleto, fd)

    def _update_amounts(self, boleto: BoletoImportado, fd: StudioFormData) -> None:
        """Parsea y asigna los montos financieros. Falla de forma controlada."""
        try:
            boleto.tarifa_base = Decimal(fd.fare.replace(",", ""))
            boleto.otros_impuestos_monto = Decimal(fd.taxes.replace(",", ""))
            boleto.total_boleto = Decimal(fd.total.replace(",", ""))
        except (InvalidOperation, AttributeError) as e:
            logger.warning(
                f"Error parseando montos del boleto {boleto.pk} (ticket={fd.ticket_no}): {e}"
            )

    def _sync_parsed_data(self, boleto: BoletoImportado, fd: StudioFormData) -> None:
        """
        Sincroniza datos_parseados con los valores del formulario.
        Mantiene compatibilidad con el esquema legacy (snake_case) y
        el nuevo esquema del VentaBuilder (UPPERCASE).
        """
        datos = boleto.datos_parseados or {}
        datos.update(
            {
                # Esquema legacy (parsers Sabre/KIU)
                "passenger_name": fd.nombre,
                "passenger_document": fd.foid,
                "pnr": fd.pnr,
                "pnr_aerolinea": fd.pnr_aerolinea,
                "airline_pnr": fd.pnr_aerolinea,
                "ticket_number": fd.ticket_no,
                "total_amount": fd.total,
                "total_currency": fd.total_currency,
                "fare_amount": fd.fare,
                "tax_details": fd.taxes,
                # Esquema God Mode (VentaBuilder)
                "NOMBRE_DEL_PASAJERO": fd.nombre,
                "CODIGO_IDENTIFICACION": fd.foid,
                "CODIGO_RESERVA": fd.pnr,
                "CODIGO_RESERVA_AEROLINEA": fd.pnr_aerolinea,
                "NUMERO_DE_BOLETO": fd.ticket_no,
                "TARIFA": fd.fare,
                "IMPUESTOS": fd.taxes,
                "TOTAL": fd.total,
                "TOTAL_MONEDA": fd.total_currency,
            }
        )
        boleto.datos_parseados = datos

    def _append_audit_log(self, boleto: BoletoImportado) -> None:
        """Añade una entrada de auditoría al log del boleto."""
        boleto.log_parseo = (
            boleto.log_parseo or ""
        ) + "\n✅ Datos actualizados manualmente vía Studio."

    def _reprocess(self, boleto: BoletoImportado, cliente_id: str | None) -> ReviewResult:
        """
        Delega el reprocesamiento al TicketParserService usando manual_only=True
        para que no vuelva a llamar a la IA y respete los montos guardados.
        """
        try:
            servicio = TicketParserService()
            venta = servicio.procesar_boleto(
                boleto.pk,
                forced_client_id=cliente_id,
                manual_only=True,
            )

            # Refrescar para detectar si el servicio completó el estado
            boleto.refresh_from_db()
            if boleto.estado_parseo == "COM" and boleto.venta_asociada:
                venta = boleto.venta_asociada

            if isinstance(venta, Venta):
                logger.info(f"Boleto {boleto.pk} reprocesado exitosamente  Venta {venta.pk}")
                return ReviewResult(success=True, venta=venta)

            error_msg = boleto.log_parseo or "Error desconocido al reprocesar."
            logger.warning(f"Boleto {boleto.pk}: reprocesamiento incompleto. {error_msg}")
            return ReviewResult(success=False, error_message=error_msg)

        except Exception as e:
            logger.exception(f"Error crítico reprocesando boleto {boleto.pk}")
            return ReviewResult(success=False, error_message=str(e))

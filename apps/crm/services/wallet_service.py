import logging
from decimal import Decimal

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import Moneda
from apps.crm.models import Cliente, MovimientoSaldoCliente
from core.api import sale_recalculation_requested

logger = logging.getLogger(__name__)


class WalletClienteService:
    """
    Servicio para la gestión de Billetera / Cuenta Corriente de Clientes.
    Controla abonos/anticipos, deducciones automáticas para pagos de ventas y reembolsos.
    """

    @classmethod
    @transaction.atomic
    def recargar_saldo(
        cls,
        cliente: Cliente,
        monto: Decimal | float | str,
        metodo_pago: str = "TRF",
        referencia: str = "",
        descripcion: str = "",
        comprobante=None,
        usuario=None,
        moneda=None,
    ) -> MovimientoSaldoCliente:
        """
        Registra un depósito/abono de saldo a favor para el cliente.
        """
        monto_dec = Decimal(str(monto)).quantize(Decimal("0.01"))
        if monto_dec <= Decimal("0.00"):
            raise ValidationError(_("El monto del depósito debe ser mayor a 0."))

        if not moneda:
            moneda, _created = Moneda.objects.get_or_create(
                codigo_iso="USD", defaults={"nombre": "Dólar Estadounidense", "simbolo": "$"}
            )

        saldo_previo = cliente.saldo_a_favor
        saldo_nuevo = saldo_previo + monto_dec

        desc_final = (
            descripcion or f"Depósito / Anticipo vía {metodo_pago} (Ref: {referencia or 'S/R'})"
        )

        movimiento = MovimientoSaldoCliente.objects.create(
            agencia=cliente.agencia,
            cliente=cliente,
            tipo_movimiento=MovimientoSaldoCliente.TipoMovimiento.DEPOSITO_ANTICIPO,
            monto=monto_dec,
            moneda=moneda,
            saldo_resultante=saldo_nuevo,
            metodo_pago_origen=metodo_pago,
            referencia_bancaria=referencia,
            comprobante=comprobante,
            descripcion=desc_final,
            registrado_por=usuario,
            creado=timezone.now(),
        )

        logger.info(
            f"💳 Saldo recargado: +${monto_dec} para Cliente #{cliente.pk} ({cliente.get_nombre_completo()}). Nuevo saldo: ${saldo_nuevo}"
        )

        # Auto-liquidar ventas pendientes del cliente o sus dependientes si existen
        cls.auto_liquidar_ventas_pendientes(cliente, usuario=usuario)

        return movimiento

    @classmethod
    @transaction.atomic
    def auto_liquidar_ventas_pendientes(cls, cliente, usuario=None):
        """
        Liquida automáticamente las ventas pendientes del cliente titular y sus pasajeros dependientes
        utilizando el saldo a favor disponible.
        """
        saldo_disponible = cliente.saldo_a_favor
        if saldo_disponible <= Decimal("0.00"):
            return []

        Venta = apps.get_model("bookings", "Venta")
        pasajeros_ids = list(
            cliente.pasajeros.filter(is_deleted=False).values_list("id_pasajero", flat=True)
        )

        from django.db.models import Q

        q_pendientes = Q(cliente=cliente, saldo_pendiente__gt=Decimal("0.00"), is_deleted=False)
        if pasajeros_ids:
            q_pendientes |= Q(
                pasajeros__id_pasajero__in=pasajeros_ids,
                saldo_pendiente__gt=Decimal("0.00"),
                is_deleted=False,
            )

        ventas_pendientes = (
            Venta.all_objects.filter(q_pendientes).distinct().order_by("fecha_venta")
        )

        pagos_aplicados = []
        for v in ventas_pendientes:
            saldo_actual = cliente.saldo_a_favor
            if saldo_actual <= Decimal("0.00"):
                break
            if v.saldo_pendiente <= Decimal("0.00"):
                continue

            monto_a_pagar = min(v.saldo_pendiente, saldo_actual)
            pago, mov = cls.aplicar_saldo_a_venta(
                venta=v,
                monto=monto_a_pagar,
                usuario=usuario,
                notas=f"Auto-liquidación con saldo disponible (Cliente #{cliente.pk})",
            )
            pagos_aplicados.append((pago, mov))
            logger.info(
                f"⚡ Venta #{v.pk} auto-liquidada con ${monto_a_pagar} de saldo de #{cliente.pk}."
            )

        return pagos_aplicados

    @classmethod
    @transaction.atomic
    def aplicar_saldo_automatico_a_venta(cls, venta, usuario=None):
        """
        Evalúa si el cliente titular o el cliente padre de algún pasajero de la venta tiene saldo a favor
        y lo aplica automáticamente a la venta.
        """
        if not venta or (venta.saldo_pendiente or Decimal("0.00")) <= Decimal("0.00"):
            return None

        cliente = venta.cliente
        if not cliente and hasattr(venta, "pasajeros"):
            for p in venta.pasajeros.all():
                cli_padre = p.clientes_asociados.filter(is_deleted=False).first()
                if cli_padre:
                    cliente = cli_padre
                    venta.cliente = cliente
                    venta.save(update_fields=["cliente"])
                    break

        if cliente and cliente.saldo_a_favor > Decimal("0.00"):
            monto_a_pagar = min(venta.saldo_pendiente, cliente.saldo_a_favor)
            pago, mov = cls.aplicar_saldo_a_venta(
                venta=venta,
                monto=monto_a_pagar,
                usuario=usuario,
                notas="Auto-deducción automática al procesar venta/boleto",
            )
            return pago, mov
        return None

    @classmethod
    @transaction.atomic
    def aplicar_saldo_a_venta(
        cls,
        venta,
        monto: Decimal | float | str | None = None,
        usuario=None,
        notas: str = "",
    ):
        """
        Deduce saldo a favor del cliente titular de la venta para pagar total o parcialmente dicha venta.
        """
        cliente = venta.cliente
        if not cliente:
            raise ValidationError(
                _("La venta debe tener un cliente asignado para aplicar saldo a favor.")
            )

        saldo_disponible = cliente.saldo_a_favor
        if saldo_disponible <= Decimal("0.00"):
            raise ValidationError(_("El cliente no posee saldo a favor disponible."))

        # Si no se especifica monto, se asume el saldo pendiente de la venta o el máximo disponible
        if monto is None:
            monto_dec = min(venta.saldo_pendiente, saldo_disponible)
        else:
            monto_dec = Decimal(str(monto)).quantize(Decimal("0.01"))

        if monto_dec <= Decimal("0.00"):
            raise ValidationError(_("El monto a pagar debe ser mayor a 0."))

        if monto_dec > saldo_disponible:
            raise ValidationError(
                _(f"Saldo insuficiente. El cliente solo dispone de ${saldo_disponible} USD.")
            )

        if monto_dec > venta.saldo_pendiente:
            monto_dec = venta.saldo_pendiente

        moneda = venta.moneda or Moneda.objects.filter(codigo_iso="USD").first()

        PagoVenta = apps.get_model("bookings", "PagoVenta")

        # 1. Crear el PagoVenta con método SAF (Saldo a Favor)
        ref = f"Deducción Billetera (Saldo previo: ${saldo_disponible})"
        pago = PagoVenta.objects.create(
            agencia=venta.agencia,
            venta=venta,
            monto=monto_dec,
            moneda=moneda,
            metodo=PagoVenta.MetodoPago.SALDO_A_FAVOR,
            referencia=ref,
            confirmado=True,
            notas=notas
            or f"Pago aplicado desde saldo a favor del cliente {cliente.get_nombre_completo()}",
        )

        saldo_nuevo = saldo_disponible - monto_dec

        # 2. Registrar el MovimientoSaldoCliente
        movimiento = MovimientoSaldoCliente.objects.create(
            agencia=cliente.agencia,
            cliente=cliente,
            tipo_movimiento=MovimientoSaldoCliente.TipoMovimiento.CONSUMO_VENTA,
            monto=monto_dec,
            moneda=moneda,
            saldo_resultante=saldo_nuevo,
            venta=venta,
            pago_venta=pago,
            metodo_pago_origen="SALDO_A_FAVOR",
            referencia_bancaria=f"Venta #{venta.pk} (PNR: {venta.localizador})",
            descripcion=f"Pago de Boleto / Servicio - Venta #{venta.pk} (PNR: {venta.localizador})",
            registrado_por=usuario,
            creado=timezone.now(),
        )

        # 3. Recalcular la venta vía señal desacoplada
        sale_recalculation_requested.send(
            sender=venta.__class__, venta_id=venta.pk, agencia_id=venta.agencia_id
        )

        logger.info(
            f"💳 Deducción de saldo aplicada: -${monto_dec} de Cliente #{cliente.pk} para Venta #{venta.pk}. Saldo restante: ${saldo_nuevo}"
        )
        return pago, movimiento

    @classmethod
    @transaction.atomic
    def reembolsar_saldo(
        cls,
        cliente: Cliente,
        monto: Decimal | float | str,
        motivo: str = "",
        referencia: str = "",
        usuario=None,
    ) -> MovimientoSaldoCliente:
        """
        Registra una devolución o egreso de dinero hacia el cliente descontándolo de su saldo a favor.
        """
        monto_dec = Decimal(str(monto)).quantize(Decimal("0.01"))
        saldo_disponible = cliente.saldo_a_favor

        if monto_dec <= Decimal("0.00"):
            raise ValidationError(_("El monto a reembolsar debe ser mayor a 0."))

        if monto_dec > saldo_disponible:
            raise ValidationError(
                _(f"Saldo insuficiente para reembolsar. Disponible: ${saldo_disponible}")
            )

        moneda = Moneda.objects.filter(codigo_iso="USD").first()
        saldo_nuevo = saldo_disponible - monto_dec

        movimiento = MovimientoSaldoCliente.objects.create(
            agencia=cliente.agencia,
            cliente=cliente,
            tipo_movimiento=MovimientoSaldoCliente.TipoMovimiento.REEMBOLSO,
            monto=monto_dec,
            moneda=moneda,
            saldo_resultante=saldo_nuevo,
            metodo_pago_origen="TRANSFERENCIA",
            referencia_bancaria=referencia,
            descripcion=motivo or f"Reembolso / Devolución a cliente (Ref: {referencia})",
            registrado_por=usuario,
            creado=timezone.now(),
        )
        return movimiento

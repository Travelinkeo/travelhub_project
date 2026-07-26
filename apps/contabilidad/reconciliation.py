import logging

from django.db import transaction

from apps.bookings.models import PagoVenta
from apps.contabilidad.models import AsientoContable
from apps.contabilidad.services import ContabilidadService
from apps.finance.models import Factura

logger = logging.getLogger(__name__)


# =========================================================================================
# 🏢 EXPLICACIÓN PARA TODO PÚBLICO (Inversores y No Programadores)
# Imagine que tiene una tienda y una caja registradora. Cada vez que vende algo, la máquina
# debería imprimir un recibo y además anotarlo en el gran libro contable de la empresa.
# A veces, la impresora se queda sin papel o la luz parpadea, y la venta queda registrada en la
# caja pero no aparece en el gran libro contable. Esto causaría problemas con el fisco (auditoría).
#
# Este servicio es como un "Auditor Interno Virtual". Corre todas las noches, revisa la caja registradora,
# compara contra el gran libro contable y, si encuentra alguna venta o pago "huérfano" que no fue anotado,
# hace la anotación contable de forma automática. De este modo, la empresa siempre tiene sus cuentas claras
# y cuadradas ante el Estado y los socios, de manera automática y sin intervención humana.
#
# 💻 EXPLICACIÓN PARA PROGRAMADORES (Technical Specs)
# ContabilidadReconciliationService actúa como una red de seguridad (fail-safe) arquitectónica
# ante el desacoplamiento de señales de base de datos o fallos del broker de mensajería (Celery/Redis).
# Su función es:
#   1. Buscar Facturas emitidas/pagadas que no tengan relación de llave foránea con un asiento contable.
#   2. Buscar Pagos (`PagoVenta`) confirmados que no tengan su correspondiente asiento por diferencial cambiario.
#   3. Reparar la inconsistencia vinculando el asiento existente (si ya se generó y solo faltaba asociar)
#      o regenerando el asiento contable de forma atómica a través de `ContabilidadService`.
# =========================================================================================
class ContabilidadReconciliationService:
    """ContabilidadReconciliationService."""

    @staticmethod
    def audit_and_reconcile():
        """
        Escanea y repara inconsistencias entre Facturas/Pagos y sus asientos contables correspondientes.
        """
        logger.info("🔎 Iniciando auditoría y reconciliación contable automática...")
        facturas_arregladas = 0
        pagos_arreglados = 0

        # 1. Reconciliar Facturas
        facturas_inconsistentes = Factura.objects.filter(
            estado__in=[
                Factura.EstadoFactura.EMITIDA,
                Factura.EstadoFactura.PAGADA,
                Factura.EstadoFactura.PARCIAL,
            ]
        ).exclude(asiento_contable_factura__isnull=False)

        for factura in facturas_inconsistentes:
            try:
                # Verificar si ya existe por referencia
                asiento = AsientoContable.objects.filter(
                    referencia_documento=factura.numero_factura, agencia=factura.agencia
                ).first()

                if asiento:
                    # Si ya existía el asiento pero no estaba vinculado en la factura
                    with transaction.atomic():
                        factura.asiento_contable_factura = asiento
                        factura.save(update_fields=["asiento_contable_factura"])
                    logger.info(
                        f"Factura {factura.numero_factura} vinculada a asiento existente {asiento.id}"
                    )
                else:
                    # Generar nuevo asiento contable y vincularlo a la factura
                    with transaction.atomic():
                        asiento = ContabilidadService.generar_asiento_desde_factura(factura)
                        factura.asiento_contable_factura = asiento
                        factura.save(update_fields=["asiento_contable_factura"])
                    facturas_arregladas += 1
            except Exception as e:
                logger.error(f"Error reconciliando factura {factura.numero_factura}: {e}")

        # 2. Reconciliar Pagos
        pagos_inconsistentes = PagoVenta.objects.filter(confirmado=True)
        for pago in pagos_inconsistentes:
            try:
                ref = f"PAGO-{pago.id_pago_venta}"
                asiento = AsientoContable.objects.filter(
                    referencia_documento=ref, agencia=pago.agencia
                ).first()

                if not asiento:
                    with transaction.atomic():
                        ContabilidadService.registrar_pago_y_diferencial(pago)
                    pagos_arreglados += 1
            except Exception as e:
                logger.error(f"Error reconciliando pago {pago.id_pago_venta}: {e}")

        logger.info(
            f"✨ Reconciliación finalizada. Facturas corregidas: {facturas_arregladas}, Pagos corregidos: {pagos_arreglados}"
        )
        return facturas_arregladas, pagos_arreglados

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.bookings.models import PagoVenta
from apps.finance.models import Factura, ItemFactura, TasaCambioBCV

from .models import AsientoContable, CuentaContable, MovimientoContable

logger = logging.getLogger(__name__)


def _debitar(asiento, cuenta, monto_usd, monto_ves):
    MovimientoContable.objects.create(
        asiento=asiento,
        cuenta=cuenta,
        tipo=MovimientoContable.TipoMovimiento.DEBITO,
        monto_usd=monto_usd,
        monto_ves=monto_ves,
    )


def _acreditar(asiento, cuenta, monto_usd, monto_ves):
    MovimientoContable.objects.create(
        asiento=asiento,
        cuenta=cuenta,
        tipo=MovimientoContable.TipoMovimiento.CREDITO,
        monto_usd=monto_usd,
        monto_ves=monto_ves,
    )


class ContabilidadService:
    @staticmethod
    def _buscar_cuenta(codigo: str):
        cuenta = CuentaContable.objects.filter(codigo=codigo).first()
        if cuenta:
            return cuenta
        prefijo = codigo[:5]
        cuenta = CuentaContable.objects.filter(
            codigo__startswith=prefijo, acepta_movimientos=True
        ).first()
        if cuenta:
            logger.warning(f"Cuenta {codigo} no encontrada, usando fallback {cuenta.codigo}")
            return cuenta
        raise ValueError(
            f"Cuenta contable {codigo} (ni prefijo {prefijo}) no encontrada en Plan Contable"
        )

    @staticmethod
    def obtener_tasa_bcv(fecha: date) -> Decimal:
        try:
            tasa = TasaCambioBCV.objects.filter(fecha=fecha).first()
            if not tasa:
                tasa = TasaCambioBCV.objects.order_by("-fecha").first()
                if tasa:
                    logger.warning(f"Usando tasa BCV de {tasa.fecha} para fecha {fecha}")
            if not tasa:
                raise ValueError(f"No hay tasa BCV disponible para {fecha}")
            return tasa.tasa_bsd_por_usd
        except Exception as e:
            logger.error(f"Error obteniendo tasa BCV: {e}")
            raise

    @staticmethod
    @transaction.atomic
    def generar_asiento_desde_factura(factura: Factura) -> AsientoContable:
        try:
            tasa_dia = factura.tasa_cambio or ContabilidadService.obtener_tasa_bcv(
                factura.fecha_emision.date()
                if hasattr(factura.fecha_emision, "date")
                else factura.fecha_emision
            )

            glosa = f"Factura {factura.numero_factura} - {factura.cliente.nombre_completo if factura.cliente else 'Cliente'}"

            asiento = AsientoContable.objects.filter(glosa=glosa, agencia=factura.agencia).first()
            if asiento:
                asiento.movimientos.all().delete()
                asiento.fecha_contable = factura.fecha_emision
                asiento.glosa = glosa
                asiento.estado = AsientoContable.EstadoAsiento.CONTABILIZADO
                asiento.save()
            else:
                asiento = AsientoContable.objects.create(
                    fecha_contable=factura.fecha_emision,
                    glosa=glosa,
                    tipo_asiento=AsientoContable.TipoAsiento.VENTAS,
                    estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
                    agencia=factura.agencia,
                )

            if factura.tipo_factura == Factura.TipoFactura.TERCEROS:
                ContabilidadService._generar_lineas_intermediacion(asiento, factura, tasa_dia)
            else:
                ContabilidadService._generar_lineas_venta_propia(asiento, factura, tasa_dia)

            if hasattr(factura, "venta_asociada") and factura.venta_asociada:
                factura.venta_asociada.asiento_contable_venta = asiento
                factura.venta_asociada.save(update_fields=["asiento_contable_venta_id"])

            logger.info(f"Asiento {asiento.id} generado para factura {factura.numero_factura}")
            return asiento

        except Exception as e:
            logger.error(f"Error generando asiento desde factura {factura.numero_factura}: {e}")
            raise

    @staticmethod
    def _generar_lineas_intermediacion(asiento: AsientoContable, factura: Factura, tasa: Decimal):
        comision_usd = factura.base_imponible
        total_cxc = comision_usd + factura.monto_iva_16 + factura.monto_igtf

        cxc = ContabilidadService._buscar_cuenta("1.1.02.02")
        ingreso = ContabilidadService._buscar_cuenta("4.1.01")
        cxp = ContabilidadService._buscar_cuenta("2.1.01.02")
        iva = ContabilidadService._buscar_cuenta("2.1.02.01")

        _debitar(asiento, cxc, total_cxc, total_cxc * tasa)
        _acreditar(asiento, ingreso, comision_usd, comision_usd * tasa)

        monto_tercero = factura.monto_total - comision_usd - factura.iva_monto - factura.igtf_monto
        if monto_tercero > 0:
            _acreditar(asiento, cxp, monto_tercero, monto_tercero * tasa)

        _acreditar(asiento, iva, factura.monto_iva_16, factura.monto_iva_16 * tasa)

        igtf = ContabilidadService._buscar_cuenta("2.1.02.03")
        if factura.monto_igtf > 0:
            _acreditar(asiento, igtf, factura.monto_igtf, factura.monto_igtf * tasa)

    @staticmethod
    def _generar_lineas_venta_propia(asiento: AsientoContable, factura: Factura, tasa: Decimal):
        cxc = ContabilidadService._buscar_cuenta("1.1.02.02")
        ingreso = ContabilidadService._buscar_cuenta("4.2")
        iva = ContabilidadService._buscar_cuenta("2.1.02.01")
        igtf = ContabilidadService._buscar_cuenta("2.1.02.03")

        _debitar(asiento, cxc, factura.monto_total, factura.monto_total * tasa)

        subtotal = factura.base_imponible + factura.base_exenta
        _acreditar(asiento, ingreso, subtotal, subtotal * tasa)

        _acreditar(asiento, iva, factura.monto_iva_16, factura.monto_iva_16 * tasa)

        if factura.monto_igtf > 0:
            _acreditar(asiento, igtf, factura.monto_igtf, factura.monto_igtf * tasa)

    @staticmethod
    @transaction.atomic
    def registrar_pago_y_diferencial(pago: PagoVenta) -> AsientoContable | None:
        try:
            venta = pago.venta
            factura = venta.factura
            if not factura:
                logger.warning(f"Pago {pago.id_pago_venta} sin factura asociada")
                return None

            tasa_factura = factura.tasa_cambio
            tasa_pago = ContabilidadService.obtener_tasa_bcv(
                pago.fecha_pago.date() if hasattr(pago.fecha_pago, "date") else pago.fecha_pago
            )

            glosa = f"Pago {pago.referencia or pago.id_pago_venta} - Venta {venta.localizador}"
            asiento = AsientoContable.objects.create(
                agencia=pago.agencia,
                fecha_contable=pago.fecha_pago,
                glosa=glosa,
                tipo_asiento=AsientoContable.TipoAsiento.DIARIO,
                estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
            )

            banco = ContabilidadService._buscar_cuenta("1.1.01.04")
            cxc = ContabilidadService._buscar_cuenta("1.1.02.02")

            _debitar(asiento, banco, pago.monto, pago.monto * tasa_pago)

            bsd_factura = pago.monto * tasa_factura
            _acreditar(asiento, cxc, pago.monto, bsd_factura)

            bsd_pago = pago.monto * tasa_pago
            diferencial_bsd = bsd_pago - bsd_factura

            if abs(diferencial_bsd) > Decimal("0.01"):
                if diferencial_bsd > 0:
                    ganancia = ContabilidadService._buscar_cuenta("7.1.01")
                    _acreditar(asiento, ganancia, Decimal("0.00"), diferencial_bsd)

                    nota_debito = ContabilidadService._generar_nota_debito_diferencial(
                        factura=factura,
                        pago=pago,
                        ganancia_bsd=diferencial_bsd,
                        tasa_factura=tasa_factura,
                        tasa_pago=tasa_pago,
                    )
                    if nota_debito:
                        cxc = ContabilidadService._buscar_cuenta("1.1.02.02")
                        iva_cta = ContabilidadService._buscar_cuenta("2.1.02.01")
                        _debitar(asiento, cxc, Decimal("0.00"), nota_debito.monto_iva_bsd)
                        _acreditar(asiento, iva_cta, Decimal("0.00"), nota_debito.monto_iva_bsd)
                        logger.info(
                            f"ND {nota_debito.numero_nota_debito} generada: IVA {nota_debito.monto_iva_bsd} BSD"
                        )
                else:
                    perdida = ContabilidadService._buscar_cuenta("7.2.01")
                    _debitar(asiento, perdida, Decimal("0.00"), abs(diferencial_bsd))

            logger.info(
                f"Asiento de pago {asiento.id} generado con diferencial {diferencial_bsd} BSD"
            )
            return asiento

        except Exception as e:
            logger.error(f"Error registrando pago {pago.id_pago_venta}: {e}")
            raise

    @staticmethod
    @transaction.atomic
    def provisionar_contribucion_inatur(mes: int, anio: int) -> AsientoContable:
        try:
            from datetime import date

            from django.db.models import Sum

            primer_dia = date(anio, mes, 1)
            if mes == 12:
                ultimo_dia = date(anio, 12, 31)
            else:
                ultimo_dia = date(anio, mes + 1, 1) - timezone.timedelta(days=1)

            ingresos_mes = MovimientoContable.objects.filter(
                asiento__fecha_contable__range=(primer_dia, ultimo_dia),
                cuenta__tipo_cuenta=CuentaContable.TipoCuenta.INGRESO,
                asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
            ).aggregate(total=Sum("monto_ves"))["total"] or Decimal("0.00")

            contribucion = ingresos_mes * Decimal("0.01")

            asiento = AsientoContable.objects.create(
                fecha_contable=ultimo_dia,
                glosa=f"Provisión INATUR 1% - {mes}/{anio}",
                tipo_asiento=AsientoContable.TipoAsiento.AJUSTE,
                estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
            )

            gasto = ContabilidadService._buscar_cuenta("6.1.05")
            pasivo = ContabilidadService._buscar_cuenta("2.1.02.02")

            _debitar(asiento, gasto, Decimal("0.00"), contribucion)
            _acreditar(asiento, pasivo, Decimal("0.00"), contribucion)

            logger.info(
                f"Provisión INATUR {mes}/{anio}: {contribucion} BSD sobre ingresos {ingresos_mes} BSD"
            )
            return asiento

        except Exception as e:
            logger.error(f"Error provisionando INATUR {mes}/{anio}: {e}")
            raise

    @staticmethod
    def _generar_nota_debito_diferencial(
        factura, pago, ganancia_bsd: Decimal, tasa_factura: Decimal, tasa_pago: Decimal
    ):
        """
        Genera Nota de Débito por IVA sobre ganancia cambiaria.
        Según normativa venezolana, la ganancia incrementa la base imponible.

        Args:
        Args:
            factura: Factura origen
            pago: PagoVenta que generó el diferencial
            ganancia_bsd: Monto de la ganancia en BSD
            tasa_factura: Tasa BCV al momento de la factura
            tasa_pago: Tasa BCV al momento del pago

        Returns:
            Factura (Nota Debito) creada o None si no aplica
        """
        try:
            # Crear Factura tipo ND
            # Nota: Esto crea una factura real. Si se prefiere solo un registro contable, usar otro modelo.
            # Aquí asumimos que se emite una Nota de Débito fiscal.

            # IVA 16% sobre la ganancia
            iva_bsd = ganancia_bsd * Decimal("0.16")
            # Convertir a USD para la ND (aproximado, ya que la ND es en base a ganancia cambiaria que es en Bs)
            # Generalmente estas ND son solo en Bs. Pero el sistema es multimoneda.
            # Usamos tasa pago para la conversion base

            monto_iva_usd = iva_bsd / tasa_pago

            nota_debito = Factura.objects.create(
                tipo_factura=Factura.TipoFactura.NOTA_DEBITO,
                factura_asociada=factura,
                cliente=factura.cliente,
                moneda=factura.moneda,
                tasa_cambio=tasa_pago,
                notas=f"Nota de Débito por Diferencial Cambiario. Factura {factura.numero_factura}. Ganancia {ganancia_bsd} BSD",
                # Totales (Reflejar IVA)
                iva_monto=monto_iva_usd,
                monto_impuestos=monto_iva_usd,
                monto_total=monto_iva_usd,  # ND por el IVA solamente? O base? Leyes venezolanas: Se factura el diferencial??
                # Normalmente se emite ND sobre el valor que aumentó.
                # Simplificación: Crear ND con los montos calculados.
                estado=Factura.EstadoFactura.EMITIDA,
            )

            # Agregar Item explicando
            ItemFactura.objects.create(
                factura=nota_debito,
                descripcion="Ajuste por Diferencial Cambiario",
                cantidad=1,
                precio_unitario=Decimal(
                    "0.00"
                ),  # La base es el diferencial, pero en este caso es un ajuste
                subtotal_item=Decimal("0.00"),
            )
            # Actualizar totales manualmente para reflejar lo deseado
            nota_debito.iva_monto = monto_iva_usd
            nota_debito.monto_total = monto_iva_usd
            nota_debito.save()

            logger.info(
                f"Nota de Débito {nota_debito.numero_factura} generada: "
                f"Ganancia {ganancia_bsd} BSD, IVA {iva_bsd} BSD"
            )

            # Retornamos un objeto que tenga atributos esperados por quien llama, o adaptamos el llamador.
            # El llamador espera 'monto_iva_bsd' y 'numero_nota_debito'
            nota_debito.monto_iva_bsd = iva_bsd
            nota_debito.numero_nota_debito = nota_debito.numero_factura

            return nota_debito

        except Exception as e:
            logger.error(f"Error generando Nota de Débito: {e}")
            return None

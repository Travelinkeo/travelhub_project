# contabilidad/reportes.py
"""
Generación de reportes contables según VEN-NIF.
Balance de Comprobación, Estado de Resultados, Balance General, Libro Diario/Mayor.
"""

from datetime import date
from decimal import Decimal

from .models import AsientoContable, CuentaContable, MovimientoContable


class ReportesContables:
    """Generador de reportes contables"""

    @staticmethod
    def balance_comprobacion(fecha_desde: date, fecha_hasta: date, moneda: str = "USD") -> dict:
        monto_field = "monto_ves" if moneda in ("BSD", "VES") else "monto_usd"

        cuentas = CuentaContable.objects.filter(acepta_movimientos=True).order_by("codigo")

        resultado = {
            "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
            "moneda": moneda,
            "cuentas": [],
            "totales": {"debe": Decimal("0"), "haber": Decimal("0")},
        }

        for cuenta in cuentas:
            movimientos = MovimientoContable.objects.filter(
                cuenta=cuenta,
                asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
                asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
            )

            debe = Decimal("0")
            haber = Decimal("0")
            for mov in movimientos:
                val = getattr(mov, monto_field) or Decimal("0")
                if mov.tipo == MovimientoContable.TipoMovimiento.DEBITO:
                    debe += val
                else:
                    haber += val

            saldo = debe - haber

            if debe != 0 or haber != 0:
                resultado["cuentas"].append(
                    {
                        "codigo": cuenta.codigo,
                        "nombre": cuenta.nombre,
                        "debe": debe,
                        "haber": haber,
                        "saldo": saldo,
                        "naturaleza": cuenta.tipo,
                        "cuenta": {
                            "codigo": cuenta.codigo,
                            "nombre": cuenta.nombre,
                            "codigo_cuenta": cuenta.codigo,
                            "nombre_cuenta": cuenta.nombre,
                        },
                    }
                )

                resultado["totales"]["debe"] += debe
                resultado["totales"]["haber"] += haber

        return resultado

    @staticmethod
    def estado_resultados(fecha_desde: date, fecha_hasta: date, moneda: str = "USD") -> dict:
        monto_field = "monto_ves" if moneda in ("BSD", "VES") else "monto_usd"

        movs_ingreso = MovimientoContable.objects.filter(
            cuenta__tipo=CuentaContable.TipoCuenta.INGRESO,
            asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        )
        ingresos = Decimal("0")
        for m in movs_ingreso:
            val = getattr(m, monto_field) or Decimal("0")
            if m.tipo == MovimientoContable.TipoMovimiento.CREDITO:
                ingresos += val
            else:
                ingresos -= val

        movs_gasto = MovimientoContable.objects.filter(
            cuenta__tipo=CuentaContable.TipoCuenta.GASTO,
            asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        )
        gastos = Decimal("0")
        for m in movs_gasto:
            val = getattr(m, monto_field) or Decimal("0")
            if m.tipo == MovimientoContable.TipoMovimiento.DEBITO:
                gastos += val
            else:
                gastos -= val

        utilidad = ingresos - gastos

        return {
            "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
            "moneda": moneda,
            "ingresos": ingresos,
            "gastos": gastos,
            "utilidad_neta": utilidad,
        }

    @staticmethod
    def balance_general(fecha_corte: date, moneda: str = "USD") -> dict:
        monto_field = "monto_ves" if moneda in ("BSD", "VES") else "monto_usd"

        movs_activo = MovimientoContable.objects.filter(
            cuenta__tipo=CuentaContable.TipoCuenta.ACTIVO,
            asiento__fecha_contable__lte=fecha_corte,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        )
        total_activos = Decimal("0")
        for m in movs_activo:
            val = getattr(m, monto_field) or Decimal("0")
            total_activos += val if m.tipo == MovimientoContable.TipoMovimiento.DEBITO else -val

        movs_pasivo = MovimientoContable.objects.filter(
            cuenta__tipo=CuentaContable.TipoCuenta.PASIVO,
            asiento__fecha_contable__lte=fecha_corte,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        )
        total_pasivos = Decimal("0")
        for m in movs_pasivo:
            val = getattr(m, monto_field) or Decimal("0")
            total_pasivos += val if m.tipo == MovimientoContable.TipoMovimiento.CREDITO else -val

        movs_patrimonio = MovimientoContable.objects.filter(
            cuenta__tipo=CuentaContable.TipoCuenta.PATRIMONIO,
            asiento__fecha_contable__lte=fecha_corte,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        )
        total_patrimonio = Decimal("0")
        for m in movs_patrimonio:
            val = getattr(m, monto_field) or Decimal("0")
            total_patrimonio += val if m.tipo == MovimientoContable.TipoMovimiento.CREDITO else -val

        return {
            "fecha_corte": fecha_corte,
            "moneda": moneda,
            "activos": total_activos,
            "pasivos": total_pasivos,
            "patrimonio": total_patrimonio,
            "total_pasivo_patrimonio": total_pasivos + total_patrimonio,
            "cuadrado": abs(total_activos - (total_pasivos + total_patrimonio)) < Decimal("0.01"),
        }

    @staticmethod
    def libro_diario(fecha_desde: date, fecha_hasta: date, moneda: str = "USD") -> list[dict]:
        monto_field = "monto_ves" if moneda in ("BSD", "VES") else "monto_usd"

        asientos = AsientoContable.objects.filter(
            fecha_contable__range=(fecha_desde, fecha_hasta),
            estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        ).order_by("fecha_contable", "id")

        resultado = []
        for asiento in asientos:
            detalles = []
            t_debe = Decimal("0")
            t_haber = Decimal("0")
            for mov in asiento.movimientos.all():
                val = getattr(mov, monto_field) or Decimal("0")
                debe = val if mov.tipo == MovimientoContable.TipoMovimiento.DEBITO else Decimal("0")
                haber = val if mov.tipo == MovimientoContable.TipoMovimiento.CREDITO else Decimal("0")
                t_debe += debe
                t_haber += haber
                detalles.append(
                    {
                        "cuenta_codigo": mov.cuenta.codigo,
                        "cuenta_nombre": mov.cuenta.nombre,
                        "cuenta_contable": {
                            "codigo": mov.cuenta.codigo,
                            "nombre": mov.cuenta.nombre,
                            "codigo_cuenta": mov.cuenta.codigo,
                            "nombre_cuenta": mov.cuenta.nombre,
                        },
                        "debe": debe,
                        "haber": haber,
                        "descripcion": mov.cuenta.nombre,
                    }
                )

            resultado.append(
                {
                    "numero": asiento.id,
                    "fecha": asiento.fecha_contable,
                    "descripcion": asiento.glosa,
                    "tipo": asiento.get_tipo_asiento_display(),
                    "detalles": detalles,
                    "total_debe": t_debe,
                    "total_haber": t_haber,
                }
            )

        return resultado

    @staticmethod
    def libro_mayor(
        cuenta_id: int, fecha_desde: date, fecha_hasta: date, moneda: str = "USD"
    ) -> dict:
        monto_field = "monto_ves" if moneda in ("BSD", "VES") else "monto_usd"
        cuenta = CuentaContable.objects.get(id=cuenta_id)

        movs_prev = MovimientoContable.objects.filter(
            cuenta=cuenta,
            asiento__fecha_contable__lt=fecha_desde,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        )
        saldo_inicial = Decimal("0")
        for m in movs_prev:
            val = getattr(m, monto_field) or Decimal("0")
            saldo_inicial += val if m.tipo == MovimientoContable.TipoMovimiento.DEBITO else -val

        movimientos = (
            MovimientoContable.objects.filter(
                cuenta=cuenta,
                asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
                asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
            )
            .select_related("asiento")
            .order_by("asiento__fecha_contable")
        )

        detalle_movimientos = []
        saldo_acumulado = saldo_inicial

        for mov in movimientos:
            val = getattr(mov, monto_field) or Decimal("0")
            debe = val if mov.tipo == MovimientoContable.TipoMovimiento.DEBITO else Decimal("0")
            haber = val if mov.tipo == MovimientoContable.TipoMovimiento.CREDITO else Decimal("0")
            saldo_acumulado += debe - haber

            detalle_movimientos.append(
                {
                    "fecha": mov.asiento.fecha_contable,
                    "asiento": mov.asiento.id,
                    "descripcion": mov.asiento.glosa or mov.cuenta.nombre,
                    "debe": debe,
                    "haber": haber,
                    "saldo": saldo_acumulado,
                }
            )

        return {
            "cuenta": {
                "codigo": cuenta.codigo,
                "nombre": cuenta.nombre,
                "codigo_cuenta": cuenta.codigo,
                "nombre_cuenta": cuenta.nombre,
                "naturaleza": cuenta.get_tipo_display(),
            },
            "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
            "moneda": moneda,
            "saldo_inicial": saldo_inicial,
            "movimientos": detalle_movimientos,
            "saldo_final": saldo_acumulado,
        }

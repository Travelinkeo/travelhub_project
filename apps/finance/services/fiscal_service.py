"""
Servicio especializado en fiscalidad y regulación para agencias de viajes en Venezuela.
Implementa:
  - Sentencia TSJ 00256 (Caso Escala): Segregación de Ventas por Cuenta de Terceros vs Ingresos Propios.
  - Guía de Doble Retención para Sujetos Pasivos Especiales (SPE): Retención IVA Aerolínea vs Retención ISLR/IVA Agencia.
  - Ley Orgánica de Turismo (Art. 13 Num. 6): Contribución del 1% INATUR / MINTUR.
  - LOCTEM (Gaceta 6.755): Base imponible municipal delimitada al margen bruto (máximo 3%).
"""

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class FiscalTurismoService:
    """Servicio de cálculo y desglose fiscal especializado."""

    ALICUOTA_INATUR_PCT = Decimal("1.00")  # 1% INATUR MINTUR
    ALICUOTA_LOCTEM_MAX_PCT = Decimal("3.00")  # 3% tope municipal LOCTEM
    RETENCION_ISLR_SERVICIOS_PCT = Decimal("2.00")  # Retención base ISLR a agencias

    @classmethod
    def calcular_desglose_tsj256(cls, items_data, tasa_bcv=Decimal("1.0")):
        """
        Calcula la segregación exigida por la Sentencia TSJ 00256 (Caso Viajes Escala, C.A.).
        Separa los montos pasantes por cuenta de terceros (boletos) de los ingresos propios (fees/comisiones).
        """
        tasa_bcv = Decimal(str(tasa_bcv or "1.0"))
        if tasa_bcv <= Decimal("0"):
            tasa_bcv = Decimal("1.0")

        monto_terceros_usd = Decimal("0.0")
        ingreso_propio_usd = Decimal("0.0")
        total_iva_usd = Decimal("0.0")

        for item in items_data:
            precio = Decimal(str(item.get("precio_unitario_usd") or item.get("monto") or "0.0"))
            cantidad = Decimal(str(item.get("cantidad") or "1.0"))
            monto_total_item = precio * cantidad
            es_pasante = item.get("es_cuenta_terceros", False) or item.get("tipo") in [
                "BOLETO",
                "BOLETO_AEREO",
                "PASAJE",
                "PASAJE_AEREO",
            ]

            if es_pasante:
                monto_terceros_usd += monto_total_item
            else:
                ingreso_propio_usd += monto_total_item

            # IVA aplicado solo a servicios o fees gravados
            if item.get("aplica_iva", False):
                tasa_iva = Decimal(str(item.get("tasa_iva") or "16.0")) / Decimal("100")
                total_iva_usd += monto_total_item * tasa_iva

        monto_terceros_ves = (monto_terceros_usd * tasa_bcv).quantize(Decimal("0.01"))
        ingreso_propio_ves = (ingreso_propio_usd * tasa_bcv).quantize(Decimal("0.01"))
        total_iva_ves = (total_iva_usd * tasa_bcv).quantize(Decimal("0.01"))

        # Aporte 1% INATUR MINTUR (sobre ingreso propio)
        inatur_usd = (ingreso_propio_usd * (cls.ALICUOTA_INATUR_PCT / Decimal("100"))).quantize(
            Decimal("0.01")
        )
        inatur_ves = (inatur_usd * tasa_bcv).quantize(Decimal("0.01"))

        # Impuesto Municipal LOCTEM (sobre ingreso propio como base imponible real)
        loctem_usd = (ingreso_propio_usd * (cls.ALICUOTA_LOCTEM_MAX_PCT / Decimal("100"))).quantize(
            Decimal("0.01")
        )
        loctem_ves = (loctem_usd * tasa_bcv).quantize(Decimal("0.01"))

        return {
            "monto_cuenta_terceros_usd": monto_terceros_usd.quantize(Decimal("0.01")),
            "monto_cuenta_terceros_ves": monto_terceros_ves,
            "ingreso_propio_agencia_usd": ingreso_propio_usd.quantize(Decimal("0.01")),
            "ingreso_propio_agencia_ves": ingreso_propio_ves,
            "total_iva_usd": total_iva_usd.quantize(Decimal("0.01")),
            "total_iva_ves": total_iva_ves,
            "monto_inatur_1_usd": inatur_usd,
            "monto_inatur_1_ves": inatur_ves,
            "base_impuesto_municipal_usd": ingreso_propio_usd.quantize(Decimal("0.01")),
            "base_impuesto_municipal_ves": ingreso_propio_ves,
            "monto_impuesto_municipal_usd": loctem_usd,
            "monto_impuesto_municipal_ves": loctem_ves,
        }

    @classmethod
    def generar_guia_retencion_spe(cls, factura):
        """
        Genera la guía detallada de retención para Clientes Institucionales / Sujetos Pasivos Especiales (SPE).
        Previene que el cliente institucionales aplique retención de ISLR sobre el total del pasaje aéreo.
        """
        tasa_bcv = Decimal(str(factura.tasa_bcv_aplicada or "1.0"))
        terceros_usd = getattr(factura, "monto_cuenta_terceros_usd", Decimal("0.0"))
        ingreso_usd = getattr(factura, "ingreso_propio_agencia_usd", Decimal("0.0"))

        # 1. Comprobante A (Aerolínea) - Retención IVA pasaje
        iva_boleto_usd = getattr(factura, "total_iva_usd", Decimal("0.0"))
        retencion_iva_boleto_75_usd = (iva_boleto_usd * Decimal("0.75")).quantize(Decimal("0.01"))
        retencion_iva_boleto_100_usd = iva_boleto_usd.quantize(Decimal("0.01"))

        # 2. Comprobante B (Agencia) - Retención ISLR (2%) + IVA sobre fee
        retencion_islr_agencia_2_usd = (
            ingreso_usd * (cls.RETENCION_ISLR_SERVICIOS_PCT / Decimal("100"))
        ).quantize(Decimal("0.01"))
        retencion_islr_agencia_3_usd = (ingreso_usd * (Decimal("3.00") / Decimal("100"))).quantize(
            Decimal("0.01")
        )

        return {
            "factura_numero": factura.numero_control,
            "fecha_emision": factura.fecha_emision,
            "tasa_bcv": tasa_bcv,
            "monto_boleto_terceros_usd": terceros_usd,
            "monto_boleto_terceros_ves": (terceros_usd * tasa_bcv).quantize(Decimal("0.01")),
            "ingreso_agencia_usd": ingreso_usd,
            "ingreso_agencia_ves": (ingreso_usd * tasa_bcv).quantize(Decimal("0.01")),
            # Comprobante A
            "comprobante_a_aerolinea": {
                "concepto": "Boleto Aéreo / Transporte por Cuenta de Terceros",
                "base_imponible_usd": terceros_usd,
                "retencion_iva_75_usd": retencion_iva_boleto_75_usd,
                "retencion_iva_75_ves": (retencion_iva_boleto_75_usd * tasa_bcv).quantize(
                    Decimal("0.01")
                ),
                "retencion_iva_100_usd": retencion_iva_boleto_100_usd,
                "retencion_iva_100_ves": (retencion_iva_boleto_100_usd * tasa_bcv).quantize(
                    Decimal("0.01")
                ),
                "nota": "La retención de IVA del pasaje debe emitirse a nombre de la Línea Aérea emisora.",
            },
            # Comprobante B
            "comprobante_b_agencia": {
                "concepto": "Honorarios por Gestión / Intermediación Turística",
                "base_imponible_usd": ingreso_usd,
                "retencion_islr_2_usd": retencion_islr_agencia_2_usd,
                "retencion_islr_2_ves": (retencion_islr_agencia_2_usd * tasa_bcv).quantize(
                    Decimal("0.01")
                ),
                "retencion_islr_3_usd": retencion_islr_agencia_3_usd,
                "retencion_islr_3_ves": (retencion_islr_agencia_3_usd * tasa_bcv).quantize(
                    Decimal("0.01")
                ),
                "nota": "La retención de ISLR (2% o 3%) aplica EXCLUSIVAMENTE sobre los honorarios/fee de la Agencia.",
            },
            "fundamento_legal": "Sentencia N° 00256 del TSJ (Caso Viajes Escala) y Art. 10 de la Ley de IVA.",
        }

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import models
from apps.finance.models.currencies import Moneda
from apps.bookings.models import Proveedor, TarifarioProveedor
from apps.common.utils import clean_currency

logger = logging.getLogger(__name__)

class FinancialEngine:
    MAX_DISCREPANCY = Decimal("0.10")

    @staticmethod
    def calculate_ticket_amounts(data, boleto_obj=None):
        """
        Extracts, normalizes, and validates financial amounts from parsed data or a boleto object.
        🛡️ Audit Step 3.2: Financial Robustness
        """
        # 1. Extracción y Limpieza Inicial
        if boleto_obj and (boleto_obj.total_boleto or 0) > 0:
            monto_base = clean_currency(boleto_obj.tarifa_base or Decimal("0.00"))
            monto_total = clean_currency(boleto_obj.total_boleto or Decimal("0.00"))
            monto_iva_yn = clean_currency(boleto_obj.iva_monto or Decimal("0.00"))
            monto_inatur = clean_currency(boleto_obj.inatur_monto or Decimal("0.00"))
            monto_otros_tax = clean_currency(boleto_obj.otros_impuestos_monto or Decimal("0.00"))
            codigo_moneda = data.get('total_currency') or data.get('moneda') or 'USD'
            logger.info(f"💰 Usando montos MANUALES del Boleto {boleto_obj.pk}: Total {monto_total}")
        else:
            # Intentar extraer de múltiples alias posibles del parser
            # Aseguramos que siempre pasen por clean_currency
            monto_base = clean_currency(data.get('tarifa') or data.get('fare_amount') or data.get('TARIFA_IMPORTE') or 0)
            monto_total = clean_currency(data.get('total') or data.get('total_amount') or data.get('TOTAL_IMPORTE') or 0)
            
            # Desglose de impuestos (IA suele enviar 'tax_details' o 'tarifas.taxes_breakdown')
            tax_data = data.get('tax_details') or data.get('tarifas', {}).get('taxes_breakdown') or {}
            
            monto_iva_yn = clean_currency(tax_data.get('iva') or tax_data.get('iva_yn') or tax_data.get('VAT') or 0)
            monto_inatur = clean_currency(tax_data.get('inatur') or tax_data.get('tourism_tax') or 0)
            monto_otros_tax = clean_currency(tax_data.get('other_taxes') or tax_data.get('otros') or 0)
            
            # Si no hay desglose, pero hay un monto total de impuestos
            if monto_iva_yn == 0 and monto_inatur == 0 and monto_otros_tax == 0:
                impuestos_total = clean_currency(data.get('taxes_amount') or data.get('impuestos') or 0)
                monto_otros_tax = impuestos_total

            codigo_moneda = data.get('moneda') or data.get('total_currency') or 'USD'

        # 2. Normalización de Moneda
        codigo_moneda = str(codigo_moneda).strip().upper()
        if not codigo_moneda or len(codigo_moneda) != 3: 
            codigo_moneda = 'USD'

        moneda_obj, _ = Moneda.objects.get_or_create(
            codigo_iso=codigo_moneda, 
            defaults={'nombre': codigo_moneda}
        )
        
        # 3. Validación de Integridad (Suma de Partes)
        suma_partes = monto_base + monto_iva_yn + monto_inatur + monto_otros_tax
        
        # Si el total es 0 pero la suma no lo es, confiamos en la suma
        if monto_total == 0 and suma_partes > 0:
            logger.info(f"⚖️ Ajustando monto_total a suma_partes ({suma_partes}) porque era 0.")
            monto_total = suma_partes
            
        discrepancia = abs(monto_total - suma_partes)
        es_integro = discrepancia <= FinancialEngine.MAX_DISCREPANCY

        if not es_integro:
            logger.warning(
                f"🚨 ALERTA FINANCIERA: Discrepancia detectada. "
                f"Total Reportado: {monto_total} | Suma Calculada: {suma_partes} | "
                f"Diferencia: {discrepancia}. PNR: {data.get('pnr') or 'N/A'}"
            )
            # En caso de discrepancia leve, forzamos la integridad ajustando 'otros impuestos'
            if discrepancia < Decimal("1.00"):
                logger.info("🔧 Autocorrigiendo discrepancia menor (<1.00) en monto_otros_tax.")
                monto_otros_tax += (monto_total - suma_partes)
                es_integro = True
                discrepancia = 0
        
        # 4. Resultado Estandarizado
        return {
            'monto_base': monto_base,
            'monto_total': monto_total,
            'monto_iva_yn': monto_iva_yn,
            'monto_inatur': monto_inatur,
            'monto_otros_tax': monto_otros_tax,
            'monto_impuestos_total': monto_iva_yn + monto_inatur + monto_otros_tax,
            'moneda_obj': moneda_obj,
            'codigo_moneda': codigo_moneda,
            'discrepancia': discrepancia,
            'es_integro': es_integro
        }


    @staticmethod
    def calculate_margins(monto_total, data, proveedor_id=None):
        """
        Calculates commission and debt with the supplier.
        """
        proveedor_obj = None
        porcentaje_comision = Decimal("0.00")
        comision_monto = Decimal("0.00")
        costo_neto_pagar = monto_total
        
        if proveedor_id:
            try:
                proveedor_obj = Proveedor.objects.get(pk=proveedor_id)
                
                tarifario = TarifarioProveedor.objects.filter(
                    proveedor=proveedor_obj,
                    activo=True,
                    fecha_vigencia_fin__gte=timezone.now().date()
                ).order_by('-fecha_carga').first()
                
                if tarifario:
                    porcentaje_comision = tarifario.comision_estandar
                    
                    nombre_air = data.get('nombre_aerolinea') or data.get('NOMBRE_AEROLINEA')
                    if nombre_air:
                        from apps.common.models import Aerolinea
                        from apps.bookings.models import ComisionOverrideAerolinea
                        
                        air_obj = Aerolinea.objects.filter(
                            models.Q(nombre__iexact=nombre_air) | 
                            models.Q(codigo_iata__iexact=nombre_air[:2])
                        ).first()
                        
                        if air_obj:
                            override = ComisionOverrideAerolinea.objects.filter(
                                tarifario=tarifario,
                                aerolinea=air_obj
                            ).first()
                            
                            if override:
                                logger.info(f"🎯 Aplicando OVERRIDE de comisión: {override.comision_porcentaje}% para {air_obj.nombre}")
                                porcentaje_comision = override.comision_porcentaje

                    comision_monto = monto_total * (porcentaje_comision / 100)
                    costo_neto_pagar = monto_total - comision_monto
                    
            except Proveedor.DoesNotExist:
                pass
        
        return {
            'proveedor_obj': proveedor_obj,
            'porcentaje_comision': porcentaje_comision,
            'comision_monto': comision_monto,
            'costo_neto_pagar': costo_neto_pagar
        }

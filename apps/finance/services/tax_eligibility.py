import logging
from decimal import Decimal
from apps.bookings.models import BoletoImportado
from apps.finance.models.tax_refund import TaxRefundOpportunity

logger = logging.getLogger(__name__)

class TaxRefundEngine:
    """
    Motor que analiza los boletos procesados buscando impuestos internacionales
    recuperables (Tax Free).
    """
    @staticmethod
    def evaluar_boleto(boleto_id):
        try:
            boleto = BoletoImportado.objects.get(pk=boleto_id)
            
            # 1. ¿Ya evaluamos este boleto? (Usamos string reference de related_name)
            if hasattr(boleto, 'tax_refund_oo'):
                return None

            # 2. Umbral Mínimo: ¿Vale la pena el trámite? (Ej. > $50 en impuestos)
            impuestos = boleto.impuestos_total_calculado or Decimal('0.00')
            if impuestos < Decimal('50.00'):
                return None

            # 3. Regla Geográfica: ¿Es vuelo internacional?
            es_internacional = False
            datos = boleto.datos_parseados or {}
            vuelos = datos.get('vuelos', [])
            
            if vuelos:
                ciudades_nacionales = ['CARACAS', 'MARACAIBO', 'VALENCIA', 'BARQUISIMETO', 'PORLAMAR', 'BARCELONA', 'PUERTO ORDAZ']
                for v in vuelos:
                    dest = str(v.get('destino', '')).upper()
                    origen = str(v.get('origen', '')).upper()
                    
                    # Si el destino u origen no están en la lista nacional, asumimos internacional
                    if dest and dest not in ciudades_nacionales:
                        es_internacional = True
                        break
            
            # 4. Decisión y Creación de la Oportunidad
            if es_internacional and impuestos >= 50:
                # Estimamos recuperar un 65% de las tasas pagadas
                monto_estimado = impuestos * Decimal('0.65') 
                
                reclamo = TaxRefundOpportunity.objects.create(
                    boleto=boleto,
                    agencia=boleto.agencia,
                    monto_estimado=monto_estimado,
                    estado=TaxRefundOpportunity.Estado.ELEGIBLE
                )
                logger.info(f"💡 [TAX REFUND] Dinero sobre la mesa: ${monto_estimado} para PNR {boleto.localizador_pnr}")
                return reclamo
                
            return None
        except Exception as e:
            logger.error(f"Error en TaxRefundEngine para boleto {boleto_id}: {e}")
            return None

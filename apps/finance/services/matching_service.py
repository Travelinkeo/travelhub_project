import logging
from decimal import Decimal
from django.db.models import Q
from apps.finance.models.facturas_proveedores import FacturaProveedor
from apps.bookings.models.venta import ItemVenta
from apps.bookings.models.servicios import Proveedor

logger = logging.getLogger(__name__)

class InvoiceMatchingService:
    """
    Servicio de Cotejo (Matching) Financiero.
    Busca correspondencia entre facturas recibidas y costos registrados en el ERP.
    """

    @staticmethod
    def auto_match_invoice(factura_proveedor_id):
        """
        Intenta conciliar automáticamente una factura de proveedor.
        Lógica:
        1. Busca proveedor por nombre (icontains).
        2. Busca ItemVenta (costos) por monto total (neto + fee) con tolerancia 1%.
        3. Prioriza si hay match de PNR/Localizador.
        """
        try:
            factura = FacturaProveedor.objects.get(pk=factura_proveedor_id)
        except FacturaProveedor.DoesNotExist:
            return False

        if factura.estado == FacturaProveedor.EstadoFactura.CONCILIADA:
            return True

        agencia_id = factura.agencia_id
        monto_factura = factura.monto_total
        moneda_codigo = factura.moneda
        proveedor_nombre_ia = (factura.proveedor_nombre or "").lower().strip()
        numero_factura = factura.numero_factura

        logger.info(f"🔍 [MATCHING] Iniciando cotejo para factura {numero_factura} de {factura.proveedor_nombre}")

        # 1. Identificar Proveedor en el ERP
        proveedor_erp = None
        if proveedor_nombre_ia:
            # Busqueda difusa simple: primeros 10 caracteres o nombre completo
            busqueda = proveedor_nombre_ia[:10]
            proveedor_erp = Proveedor.objects.filter(
                agencia_id=agencia_id,
                nombre__icontains=busqueda
            ).first()

        # 2. Buscar candidatos en ItemVenta (Costos de Ventas)
        # Nota: La moneda en ItemVenta viene de la Venta asociada
        candidatos = ItemVenta.objects.filter(
            agencia_id=agencia_id,
            venta__moneda=moneda_codigo,
            estado_item__in=['PCO', 'CNF', 'UTI'] # Pendiente, Confirmado o Utilizado
        ).select_related('venta', 'proveedor_servicio')

        if proveedor_erp:
            # Si encontramos el proveedor, priorizamos sus items, pero no excluimos otros 
            # (por si la IA detectó mal el nombre pero el monto/PNR es exacto)
            pass

        potential_matches = []
        
        for c in candidatos:
            # El costo para la agencia es Costo Neto + Fee Proveedor
            costo_neto = c.costo_neto_proveedor or Decimal('0.00')
            fee_prov = c.fee_proveedor or Decimal('0.00')
            costo_total_erp = costo_neto + fee_prov
            
            # Margen de tolerancia del 1% (máximo $10 por defecto para evitar falsos positivos en montos gigantes)
            tolerancia = min(monto_factura * Decimal('0.01'), Decimal('10.00'))
            match_monto = abs(costo_total_erp - monto_factura) <= tolerancia
            
            # Match por Referencia (PNR / Localizador)
            # Buscamos el localizador de la venta o el codigo_reserva_proveedor en el JSON de la factura
            pnr_erp = (c.codigo_reserva_proveedor or "").upper()
            loc_venta = (c.venta.localizador or "").upper()
            
            raw_data_str = str(factura.datos_json).upper()
            match_pnr = (pnr_erp and pnr_erp in raw_data_str) or (loc_venta and loc_venta in raw_data_str)

            score = 0
            if match_monto: score += 50
            if match_pnr: score += 100
            if proveedor_erp and c.proveedor_servicio == proveedor_erp: score += 30
            
            if score >= 80: # Umbral de confianza
                potential_matches.append((c, score))

        # Ordenar por score descendente
        potential_matches.sort(key=lambda x: x[1], reverse=True)

        # 3. RESOLUCIÓN
        if len(potential_matches) == 1 or (len(potential_matches) > 1 and potential_matches[0][1] > potential_matches[1][1] + 20):
            # Caso ideal: un solo match claro o uno con score significativamente mayor
            match, score = potential_matches[0]
            
            factura.estado = FacturaProveedor.EstadoFactura.CONCILIADA
            factura.proveedor = proveedor_erp or match.proveedor_servicio
            
            # Guardar referencia en metadatos
            if not factura.datos_json: factura.datos_json = {}
            factura.datos_json['matched_item_id'] = match.id_item_venta
            factura.datos_json['match_score'] = score
            factura.datos_json['matched_pnr'] = match.codigo_reserva_proveedor
            factura.save()
            
            logger.info(f"🎯 [MATCH SUCCESS] Factura {numero_factura} conciliada con Item {match.id_item_venta} (Score: {score})")
            return True
        
        elif len(potential_matches) > 1:
            factura.estado = FacturaProveedor.EstadoFactura.REQUIERE_REVISION
            if not factura.datos_json: factura.datos_json = {}
            factura.datos_json['posibles_candidatos'] = [m[0].id_item_venta for m in potential_matches[:3]]
            factura.save()
            logger.warning(f"⚠️ [MATCH AMBIGUOUS] Múltiples candidatos para factura {numero_factura}")
            return False
        
        else:
            factura.estado = FacturaProveedor.EstadoFactura.REQUIERE_REVISION
            factura.save()
            logger.info(f"❓ [MATCH NOT FOUND] No se encontró contraparte automática para factura {numero_factura}")
            return False

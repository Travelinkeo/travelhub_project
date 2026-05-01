# -*- coding: utf-8 -*-
import logging
import os
from decimal import Decimal
from django.db.models import Q
from apps.bookings.models import BoletoImportado
from core.models_catalogos import Proveedor, Aerolinea, Moneda

# SERVICIOS
from core.services.catalog_service import CatalogNormalizationService

logger = logging.getLogger(__name__)

class BoletoPersistenceService:
    """
    🎯 Responsabilidad: Guardar y versionar registros de BoletoImportado en la DB.
    """

    @staticmethod
    def update_boleto_from_data(boleto, data):
        """Actualiza los campos del modelo BoletoImportado con la data normalizada."""
        try:
            # 🛡️ FIX SEGURIDAD: Si data es un string (JSON), lo parseamos
            import json
            d = data
            if isinstance(d, str):
                try: d = json.loads(d)
                except: d = {}
            
            if not isinstance(d, dict):
                d = {}
            
            # 1. Identificación básica
            boleto.localizador_pnr = BoletoPersistenceService._truncate(d.get('pnr'), 20)
            boleto.numero_boleto = BoletoPersistenceService._truncate(d.get('ticket_number'), 50)
            
            # 2. Pasajero
            p_name = d.get('passenger_name')
            if p_name:
                p_name = str(p_name).split(' FOID')[0].split(' RIF')[0].strip()
            boleto.nombre_pasajero_completo = BoletoPersistenceService._truncate(p_name, 150)
            boleto.nombre_pasajero_procesado = BoletoPersistenceService._truncate(d.get('SOLO_NOMBRE_PASAJERO') or p_name, 150)
            boleto.foid_pasajero = BoletoPersistenceService._truncate(d.get('passenger_document'), 50)

            # 3. Aerolínea y Proveedor
            boleto.aerolinea_emisora = BoletoPersistenceService._truncate(d.get('issuing_airline'), 150)
            iata_code = d.get('agencia_iata') or d.get('agency_iata')
            
            if not iata_code and boleto.aerolinea_emisora:
                aero_obj = Aerolinea.objects.filter(nombre__icontains=boleto.aerolinea_emisora).first()
                if aero_obj: iata_code = aero_obj.codigo_iata

            office_id = d.get('office_id')
            boleto.proveedor_emisor = BoletoPersistenceService._find_provider(iata_code, office_id)

            # 4. Financiero
            from core.services.parsers.normalization import DataNormalizationService
            boleto.total_boleto = DataNormalizationService.safe_decimal(d.get('total_amount'))
            boleto.tarifa_base = DataNormalizationService.safe_decimal(d.get('fare_amount'))
            
            # Impuestos detallados
            desglose = d.get('tarifas', {}).get('taxes_breakdown') or d.get('taxes_breakdown', {})
            boleto.iva_monto = DataNormalizationService.safe_decimal(desglose.get('iva') or desglose.get('VAT'))
            boleto.inatur_monto = DataNormalizationService.safe_decimal(desglose.get('inatur') or desglose.get('tourism_tax'))
            boleto.otros_impuestos_monto = DataNormalizationService.safe_decimal(desglose.get('otros') or desglose.get('other_taxes'))
            
            tax_total = d.get('taxes_amount') or (boleto.iva_monto + boleto.inatur_monto + boleto.otros_impuestos_monto)
            boleto.impuestos_total_calculado = DataNormalizationService.safe_decimal(tax_total)

            # 5. Metadatos y Moneda
            moneda_code = d.get('total_currency') or d.get('moneda') or 'USD'
            boleto.moneda = CatalogNormalizationService.normalize_currency(moneda_code)
            
            boleto.ruta_vuelo = d.get('ItinerarioFinalLimpio')
            boleto.datos_parseados = d
            
            # Fecha de emisión
            fecha_str = d.get('issue_date')
            if fecha_str:
                from core.ticket_parser import _parse_date_robust
                boleto.fecha_emision_boleto = _parse_date_robust(fecha_str)

            boleto.save()
            return boleto
        except Exception as e:
            logger.error(f"Error en BoletoPersistenceService: {e}", exc_info=True)
            raise

    @staticmethod
    def handle_versioning(boleto):
        """Gestiona versiones de re-emisión si el número de boleto ya existe."""
        if not boleto.numero_boleto: return
        
        duplicados = BoletoImportado.objects.filter(
            numero_boleto=boleto.numero_boleto
        ).exclude(pk=boleto.pk).order_by('-version')

        ultimo = duplicados.first()
        if ultimo:
            boleto.version = ultimo.version + 1
            boleto.boleto_padre = ultimo
            boleto.estado_emision = BoletoImportado.EstadoEmision.REEMISION
            boleto.save(update_fields=['version', 'boleto_padre', 'estado_emision'])

    @staticmethod
    def _truncate(val, max_len):
        if not val: return None
        s = str(val).strip()
        return s[:max_len]

    @staticmethod
    def _find_provider(iata, office_id):
        if not iata and not office_id: return None
        try:
            candidatos = Proveedor.objects.filter(identificadores_gds__isnull=False)
            for prov in candidatos:
                gds_ids = prov.identificadores_gds
                if not isinstance(gds_ids, dict): continue
                if iata and iata in gds_ids.get('IATA', []): return prov
                if office_id and office_id in gds_ids.get('OFFICE_ID', []): return prov
        except: pass
        return None

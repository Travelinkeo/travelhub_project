import logging
from apps.common.models import Ciudad
from apps.bookings.models import SegmentoVuelo
from core.services.catalog_service import CatalogNormalizationService
from core.ticket_parser import _parse_date_robust

logger = logging.getLogger(__name__)

class ItineraryService:
    @staticmethod
    def sync_segments(data, agencia, venta, item_venta_obj, aerolinea_default):
        """
        Synchronizes flight segments for a sale.
        """
        itinerario = data.get('segmentos') or data.get('itinerario') or data.get('flights', [])
        
        for seg in itinerario:
            try:
                # Resolve Cities
                iata_dep = seg.get('codigo_iata_origen')
                iata_arr = seg.get('codigo_iata_destino')

                ciudad_dep = None
                ciudad_arr = None

                if iata_dep:
                    ciudad_dep = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_dep)
                if iata_arr:
                    ciudad_arr = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_arr)

                if not ciudad_dep:
                    dep_loc = seg.get('origen') or seg.get('departure', {}).get('location') or 'N/A'
                    clean_name = str(dep_loc).split(',')[0].split('(')[0].strip()
                    ciudad_dep = Ciudad.objects.filter(nombre__iexact=clean_name).first()
                
                if not ciudad_arr:
                    arr_loc = seg.get('destino') or seg.get('arrival', {}).get('location') or 'N/A'
                    clean_name = str(arr_loc).split(',')[0].split('(')[0].strip()
                    ciudad_arr = Ciudad.objects.filter(nombre__iexact=clean_name).first()

                # Sync Segment
                vuelo_num = str(seg.get('vuelo') or seg.get('flightNumber') or seg.get('flight_number') or "N/A")
                f_salida = _parse_date_robust(str(seg.get('fecha_salida') or seg.get('date')))
                
                seg_existente = SegmentoVuelo.objects.filter(
                    venta=venta,
                    numero_vuelo=vuelo_num,
                    fecha_salida=f_salida
                ).first()

                seg_data = {
                    'agencia': agencia,
                    'venta': venta,
                    'item_venta': item_venta_obj,
                    'origen': ciudad_dep,
                    'destino': ciudad_arr,
                    'aerolinea': seg.get('airline') or seg.get('aerolinea') or aerolinea_default,
                    'numero_vuelo': vuelo_num,
                    'clase_reserva': str(seg.get('details', {}).get('cabin') or seg.get('clase') or 'Y')[:5],
                    'fecha_salida': f_salida,
                    'fecha_llegada': _parse_date_robust(str(seg.get('fecha_llegada'))),
                }

                if seg_existente:
                    for key, value in seg_data.items():
                        setattr(seg_existente, key, value)
                    seg_existente.save()
                    logger.info(f"✈️ SegmentoVuelo actualizado: {vuelo_num}")
                else:
                    SegmentoVuelo.objects.create(**seg_data)
                    logger.info(f"✈️ SegmentoVuelo creado: {vuelo_num}")

            except Exception as seg_err:
                logger.error(f"Error procesando segmento de vuelo: {seg_err}")

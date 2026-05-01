from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import Cotizacion, ItemCotizacion
from .serializers import CotizacionSerializer, ItemCotizacionSerializer
from .pdf_service import generar_pdf_cotizacion
from django.views.generic import TemplateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from .ai_schemas import CotizacionMagicSchema
from core.services.ai_engine import ai_engine
import os
import json
import logging
import time
import re
import requests
try:
    from apps.contabilidad.models import TasaCambioBCV
except ImportError:
    TasaCambioBCV = None


# Regex para identificar aerolíneas en texto crudo de GDS
re_airlines = re.compile(r'\b([A-Z0-9]{2,3})\s+\d{2,4}\b', re.IGNORECASE)


logger = logging.getLogger(__name__)


class CotizacionViewSet(viewsets.ModelViewSet):
    queryset = Cotizacion.objects.select_related('cliente', 'consultor').prefetch_related('items_cotizacion').order_by('-fecha_emision')
    serializer_class = CotizacionSerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['post'])
    def convertir_a_venta(self, request, pk=None):
        """Convierte la cotización en una venta"""
        cotizacion = self.get_object()
        
        try:
            venta = cotizacion.convertir_a_venta()
            return Response({
                'message': 'Cotización convertida exitosamente',
                'venta_id': venta.id_venta,
                'localizador': venta.localizador
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def marcar_enviada(self, request, pk=None):
        """Marca la cotización como enviada"""
        cotizacion = self.get_object()
        cotizacion.estado = Cotizacion.EstadoCotizacion.ENVIADA
        cotizacion.fecha_envio = timezone.now()
        cotizacion.email_enviado = True
        cotizacion.save(update_fields=['estado', 'fecha_envio', 'email_enviado'])
        
        return Response({'message': 'Cotización marcada como enviada'})
    
    @action(detail=True, methods=['post'])
    def marcar_vista(self, request, pk=None):
        """Marca la cotización como vista por el cliente"""
        cotizacion = self.get_object()
        if cotizacion.estado == Cotizacion.EstadoCotizacion.ENVIADA:
            cotizacion.estado = Cotizacion.EstadoCotizacion.VISTA
            cotizacion.fecha_vista = timezone.now()
            cotizacion.save(update_fields=['estado', 'fecha_vista'])
        
        return Response({'message': 'Cotización marcada como vista'})
    
    @action(detail=True, methods=['get'])
    def preview_html(self, request, pk=None):
        """Visualizar cotización en HTML"""
        cotizacion = self.get_object()
        return render(request, 'cotizaciones/plantilla_cotizacion.html', {'cotizacion': cotizacion})

    @action(detail=True, methods=['get'])
    def preview_pdf(self, request, pk=None):
        """Visualizar/Descargar cotización en PDF"""
        cotizacion = self.get_object()
        try:
            pdf_bytes = generar_pdf_cotizacion(cotizacion)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            filename = f"Cotizacion_{cotizacion.numero_cotizacion}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        except RuntimeError as e:
             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ItemCotizacionViewSet(viewsets.ModelViewSet):
    queryset = ItemCotizacion.objects.select_related('cotizacion').all()
    serializer_class = ItemCotizacionSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        item = serializer.save()
        item.cotizacion.calcular_total()
    
    def perform_update(self, serializer):
        item = serializer.save()
        item.cotizacion.calcular_total()
    
    def perform_destroy(self, instance):
        cotizacion = instance.cotizacion
        instance.delete()
        cotizacion.calcular_total()

# --- VISTAS DEL COTIZADOR MÁGICO (GOD MODE) ---

class MagicQuoterView(LoginRequiredMixin, TemplateView):
    """
    Vista principal del Cotizador Mágico. Interfaz Alpine.js + Tailwind.
    """
    template_name = 'cotizaciones/magic_quoter.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead_id = self.request.GET.get('lead_id')
        if lead_id:
            try:
                from apps.crm.models_lead import OportunidadViaje
                context['lead'] = OportunidadViaje.objects.filter(pk=lead_id).first()
            except ImportError:
                pass
        
        # Inyectar Tasa BCV para Calculadora Integrada
        try:
            tasa = TasaCambioBCV.objects.latest('fecha')
            context['tasa_bcv'] = float(tasa.tasa_bsd_por_usd)
        except Exception:
            context['tasa_bcv'] = 0
            
        return context

class MagicQuoterAIView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para invocar a Gemini y estructurar el texto crudo de GDS.
    """
    def post(self, request, *args, **kwargs):
        # Manejar tanto peticiones de formulario como JSON
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                raw_text = data.get('raw_text', '')
                agency_fee = data.get('agency_fee', 0)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'JSON inválido'}, status=400)
        else:
            raw_text = request.POST.get('raw_text', '')
            agency_fee = request.POST.get('agency_fee', 0)
        
        # Inicialización de seguridad para evitar NameError
        dates_str = None
        outbound = None
        return_date = None
        destination = "Varios"
        base_price = 0
        final_total = 0
        clean_flights = []
        image_url = ""
        search_query = ""
        ai_output = {}
        
        if not raw_text:
            return JsonResponse({'error': 'No se detectó texto crudo GDS.'}, status=400)

        # Instrucción Maestra para Gemini (V2.0 PROMPT: Más vendedora)
        sys_prompt = (
            "Eres el motor Obsidian AI de TravelHub. Analiza el texto GDS y devuelve un JSON ESTRICTO con:\n"
            "- destination: nombre completo de la ciudad destino principal (ej: 'Shanghai', 'Madrid').\n"
            "- destination_description: una frase corta, inspiradora y formal para el cliente que describa el destino (ej: 'Descubra la magia milenaria de Shanghai' o 'Disfrute de la elegancia y cultura de Madrid').\n"
            "- image_search_query: una frase en inglés para buscar una imagen de alta calidad del destino (ej: 'Shanghai skyline night' o 'Madrid city center plaza').\n"
            "- outboundDate y returnDate en formato '20 Abr'.\n"
            "- flights: lista de segmentos. Cada uno con:\n"
            "  * airline: NOMBRE COMPLETO de la aerolínea.\n"
            "  * departureDate: fecha del vuelo en formato '20 Abr'.\n"
            "  * departureCode, arrivalCode: códigos IATA (3 letras).\n"
            "  * departureCity, arrivalCity: nombre completo de la ciudad.\n"
            "  * departureTime, arrivalTime: hora HH:MM.\n"
            "  * stops: 'Directo' o 'Con escala'.\n"
            "  * baggage: info de equipaje si existe (ej: '23kg included').\n"
            "- totalPrice: precio numérico total.\n\n"
            "REGLAS DE ORO: Nombres reales SIEMPRE. Tono formal (use 'Le' no 'Te'). No inventes datos que no existan, usa 'No especificado' si falta."
        )


        try:
            print(f"DEBUG: MagicQuoterAIView hit with {len(raw_text)} chars")
            start = time.time()
            
            data = ai_engine.call_gemini(
                prompt=f"Extract trip details from this GDS text:\n\n{raw_text}",
                system_instruction=sys_prompt,
                response_schema=CotizacionMagicSchema
            )
            
            print(f"DEBUG: Gemini response received in {time.time() - start:.2f}s")
            
            if not data or not isinstance(data, dict):
                logger.error(f"Gemini returned invalid data for MagicQuoter: {type(data)}")
                return JsonResponse({'error': 'La IA no devolvió datos válidos.'}, status=500)
            
            if 'error' in data:
                print(f"DEBUG: Gemini returned error: {data['error']}")
                return JsonResponse(data, status=400)

            # --- DICCIONARIO DE EMERGENCIA IATA ---
            IATA_MAP = {
                'CCS': 'Caracas', 'IST': 'Estambul', 'PVG': 'Shanghai', 
                'MAD': 'Madrid', 'BOG': 'Bogotá', 'MIA': 'Miami',
                'EZE': 'Buenos Aires', 'CDG': 'París', 'JFK': 'Nueva York'
            }

            # --- EXTRACCIÓN HÍBRIDA ---
            raw_flights = data.get('flights', [])
            if not raw_flights:
                segments = re.findall(r"\d+\s+[A-Z0-9]{2}\s+\d+[A-Z]?\s+\d+[A-Z]{3}\s+\d+\s+([A-Z]{3})([A-Z]{3})", raw_text)
                for dep, arr in segments:
                    raw_flights.append({'departureCode': dep, 'arrivalCode': arr, 'airline': 'Revisar GDS'})

            # Destino: Si no hay, usar llegada del primer tramo
            destination = data.get('destination')
            dest_description = data.get('destination_description', 'Su propuesta de viaje personalizada.') 
            image_search_query = data.get('image_search_query')

            if not destination and raw_flights:
                first_arrival = raw_flights[0].get('arrivalCode')
                destination = IATA_MAP.get(first_arrival, first_arrival)
            
            # Precio
            raw_base = data.get('totalPrice') or 0
            try:
                base_price = float(raw_base)
            except (ValueError, TypeError):
                base_price = 0
                
            if base_price < 100:
                prices = re.findall(r"(?:TOTAL|TKT|USD|FARE)\s*[:]?\s*(\d+(?:\.\d{2})?)", raw_text.upper())
                if prices: base_price = float(prices[-1])

            # Fechas y Rango (Recuperación)
            dates_str = data.get('dates')
            outbound = data.get('outboundDate') or data.get('outbound_date')
            return_date = data.get('returnDate') or data.get('return_date')

            if not outbound and dates_str:
                if ' - ' in dates_str:
                    parts = dates_str.split(' - ')
                    outbound = parts[0]
                    return_date = parts[1] if len(parts) > 1 else None
                else: outbound = dates_str

            # --- RESOLUCIÓN DE AEROLÍNEAS DESDE CATÁLOGO DE BASE DE DATOS ---
            # Estrategia de 2 capas para máxima precisión:
            # CAPA 1 (Verdad absoluta): extraer código IATA del texto GDS crudo via regex.
            #   Ej: " QL 450" → "QL" → BD → "Laser Airlines"
            # CAPA 2 (Fallback): usar el nombre que devolvió Gemini, si es código de 2 letras.
            # Esto evita que Gemini "alucine" aerolíneas por contexto de ruta (ej: QL→Wingo).
            from core.airline_utils import get_airline_name_by_code

            # Pre-extraer todos los códigos de vuelo del texto GDS.
            gds_flight_codes = re_airlines.findall(raw_text)
            # gds_flight_codes[0] → aerolínea del segmento 1
            # gds_flight_codes[1] → aerolínea del segmento 2, etc.



            clean_flights = []
            for idx, f in enumerate(raw_flights):
                dep_code = f.get('departureCode', '???')
                arr_code = f.get('arrivalCode', '???')

                # --- CAPA 1: Código extraído del GDS crudo (fuente de verdad) ---
                # Intentar identificar aerolínea con regex como fallback
                gds_flight_codes = re_airlines.findall(raw_text)
                airline_code = gds_flight_codes[idx] if idx < len(gds_flight_codes) else "YY"
                
                clean_airline = None
                # Excluir palabras que no son códigos IATA reales
                EXCLUIDOS = {'NO', 'HK', 'OK', 'SS', 'SA', 'WL', 'UC', 'UN', 'NN'}
                if airline_code not in EXCLUIDOS:
                    nombre_bd = get_airline_name_by_code(airline_code)
                    if nombre_bd:
                        clean_airline = nombre_bd  # ✅ Encontrado en BD

                # --- CAPA 2: Fallback → lo que devolvió Gemini ---
                if not clean_airline:
                    raw_airline = (f.get('airline', '') or '').strip()
                    if len(raw_airline) == 2 and raw_airline.isalpha():
                        # Gemini devolvió código → buscar en BD
                        nombre_bd = get_airline_name_by_code(raw_airline.upper())
                        clean_airline = nombre_bd if nombre_bd else raw_airline
                    else:
                        # Gemini devolvió nombre completo (puede ser hallucination o correcto)
                        clean_airline = raw_airline or 'Aerolínea'


                f_clean = {
                    'airline': clean_airline,
                    'departureDate': f.get('departureDate') or f.get('departure_date'),
                    'departureCode': dep_code,
                    'arrivalCode': arr_code,
                    'departureCity': f.get('departureCity') or IATA_MAP.get(dep_code),
                    'arrivalCity': f.get('arrivalCity') or IATA_MAP.get(arr_code),
                    'departureTime': f.get('departureTime', '--:--'),
                    'arrivalTime': f.get('arrivalTime', '--:--'),
                    'stops': f.get('stops', 'Directo'),
                    'baggage': f.get('baggage', '1 Maleta')
                }
                # Imagen de Destino:
                # Priorizar la consulta estructurada que generó la IA (V2.0)
                search_query = image_search_query or data.get('image_search_query') or destination
                image_url = ""
                clean_flights.append(f_clean)

            # Cálculo Final con el Fee (Unificado para JSON y POST)
            try:
                # Ya extrajimos agency_fee al inicio del método
                actual_fee = float(agency_fee)
            except (ValueError, TypeError):
                actual_fee = 50
                
            final_total = round(float(base_price) + actual_fee, 2)

            unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
            if unsplash_key:
                try:
                    res = requests.get(
                        f"https://api.unsplash.com/search/photos?query={search_query}&client_id={unsplash_key}&per_page=1",
                        timeout=3
                    )
                    if res.status_code == 200:
                        img_data = res.json()
                        if img_data.get('results'):
                            image_url = img_data['results'][0]['urls']['regular']
                except Exception:
                    pass

            ai_output = {
                'destination': destination,
                'type': data.get('type', 'Vuelo'),
                'dates': dates_str or (f"{outbound} - {return_date}" if return_date else outbound),
                'outboundDate': outbound or 'Por confirmar',
                'returnDate': return_date,
                'flights': clean_flights,
                'totalPrice': base_price,
                'currency': data.get('currency', 'USD'),
                'totalPriceWithFee': final_total,
                'image': image_url,
                'image_search_query': search_query,
                'destination_description': dest_description,
                'notas_ia': data.get('notas_ia', '')
            }

            return JsonResponse(ai_output)
        except Exception as e:
            logger.error(f"Error en MagicQuoterAIView: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

class MagicQuoterSaveView(LoginRequiredMixin, View):
    """
    Guarda la cotización generada por IA en la base de datos.
    Vincula el Lead si existe y devuelve el UUID para compartir.
    """
    def post(self, request, *args, **kwargs):
        import json
        from django.urls import reverse
        try:
            data = json.loads(request.body)
            lead_id = data.get('lead_id')
            ai_data = data.get('ai_data')
            agency_fee = data.get('agency_fee', 0)
            raw_text = data.get('raw_text', '')
            parsed_data = ai_data.get('parsed_data', {})

            if not ai_data:
                return JsonResponse({'error': 'No hay datos de IA para guardar'}, status=400)

            lead = None
            if lead_id:
                from apps.crm.models_lead import OportunidadViaje
                lead = OportunidadViaje.objects.filter(id=lead_id).first()

            # Asegurar Moneda (Evitar nulos en codigo_iso)
            from core.models_catalogos import Moneda
            currency_raw = ai_data.get('currency') or 'USD'
            currency_code = str(currency_raw).strip().upper()[:3]
            
            if not currency_code: # Fallback absoluto
                currency_code = 'USD'

            moneda, _ = Moneda.objects.get_or_create(
                codigo_iso=currency_code, 
                defaults={'nombre': 'Dólar Estadounidense' if currency_code == 'USD' else currency_code, 'simbolo': '$'}
            )

            # Estructurar la Cotización
            nombre_final = "Prospecto IA"
            cliente_vinculado = getattr(lead, 'cliente', None)
            if cliente_vinculado:
                nombre_final = cliente_vinculado.get_full_name()
            else:
                nombre_final = getattr(lead, 'nombre_cliente', 'Prospecto (Lead)')

            cotizacion = Cotizacion.objects.create(
                cliente=cliente_vinculado,
                nombre_cliente_manual=nombre_final,
                destino=ai_data.get('destination', 'Varios'),
                consultor=request.user,
                moneda=moneda,
                gds_raw_text=raw_text,
                agency_fee=agency_fee,
                metadata_ia=ai_data,
                image_url=ai_data.get('image', ''),
                total_cotizado=ai_data.get('totalPriceWithFee', 0),
                estado='BOR'
            )

            # Asegurar Producto/Servicio (Requerido por DB según error anterior)
            from core.models_catalogos import ProductoServicio
            default_producto = ProductoServicio.objects.filter(tipo_producto='VUE').first() or ProductoServicio.objects.first()

            # Guardar items para histórico financiero
            for flight in ai_data.get('flights', []):
                dep = flight.get('departureCode', '???')
                arr = flight.get('arrivalCode', '???')
                f_date = flight.get('departureDate', '')
                ItemCotizacion.objects.create(
                    cotizacion=cotizacion,
                    tipo_item='VUE',
                    producto_servicio=default_producto,
                    descripcion=f"{f_date} | {flight.get('airline')}: {dep} - {arr}",
                    subtotal_item=0,
                    total_item=0,
                    costo=0 
                )

            # Armar la URL absoluta para compartir por WhatsApp
            public_url = request.build_absolute_uri(
                reverse('cotizaciones:public_quote', kwargs={'quote_uuid': str(cotizacion.uuid)})
            )

            # Link de aprobación automática (Pre-rellena un mensaje de vuelta para el cliente)
            # El cliente al darle clic, te enviará a TI (o al que le envió el link) un mensaje de aprobación.
            approval_text = f"✅ ¡Hola! Apruebo la cotización para {cotizacion.destino}. Por favor, procede con la reserva. (Ref: {cotizacion.numero_cotizacion})"
            approval_link = f"https://wa.me/?text={approval_text.replace(' ', '%20')}"

            whatsapp_msg = (
                f"PROPUESTA DE VIAJE: {cotizacion.destino.upper()}\n\n"
                f"Hola! Te envio el itinerario personalizado que preparamos para ti.\n\n"
                f"Puedes ver el detalle, fotos y precios aqui:\n"
                f"{public_url}\n\n"
                f"Quedo atento a tus comentarios!"
            )

            return JsonResponse({
                'success': True,
                'uuid': str(cotizacion.uuid),
                'public_url': public_url,
                'whatsapp_msg': whatsapp_msg
            })

        except Exception as e:
            logger.error(f"Error guardando cotización mágica: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

class PublicQuoteDetailView(DetailView):
    """
    Visualización pública para el cliente final a través del UUID de la cotización.
    Incluye lógica de reparación de metadatos para retrocompatibilidad.
    """
    model = Cotizacion
    template_name = 'cotizaciones/public_quote.html'
    context_object_name = 'quote'
    
    def get_object(self, queryset=None):
        return get_object_or_404(Cotizacion, uuid=self.kwargs.get('quote_uuid'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quote = context['quote']
        meta = quote.metadata_ia or {}
        
        # --- REPARACIÓN AGRESIVA PARA LINKS ANTIGUOS ---
        
        # 1. Normalizar Destino (Evitar el "Varios")
        if meta.get('destination') in [None, 'Varios', '']:
            meta['destination'] = meta.get('title') or quote.destino or 'Tu Viaje'

        # 2. Normalizar Fechas
        if not meta.get('outboundDate'):
            dates = meta.get('dates', '')
            meta['outboundDate'] = dates.split(' - ')[0] if ' - ' in dates else (dates or 'Por confirmar')
        
        # 3. Normalizar Vuelos (Mapear 'route' y 'time' a campos nuevos + Ciudades)
        clean_flights = []
        flights_list = meta.get('flights', [])
        for i, f in enumerate(flights_list):
            route = f.get('route', '')
            time_str = f.get('time', '')
            
            # Códigos
            f['departureCode'] = f.get('departureCode') or (route.split(' - ')[0] if ' - ' in route else '???')
            f['arrivalCode'] = f.get('arrivalCode') or (route.split(' - ')[1] if ' - ' in route else '???')
            
            # Ciudades (Inferencia Inteligente)
            if not f.get('departureCity') or f.get('departureCity') == "Cargando...":
                if i == 0: f['departureCity'] = 'Origen'
                elif i > 0: f['departureCity'] = clean_flights[i-1].get('arrivalCity', 'Escala')
            
            if not f.get('arrivalCity') or f.get('arrivalCity') == "Cargando...":
                if i == len(flights_list) - 1: f['arrivalCity'] = meta.get('destination', 'Destino')
                else: f['arrivalCity'] = 'Conexión'

            # Horas
            f['departureTime'] = f.get('departureTime') or (time_str.split(' - ')[0] if ' - ' in time_str else '--:--')
            f['arrivalTime'] = f.get('arrivalTime') or (time_str.split(' - ')[1] if ' - ' in time_str else '--:--')
            
            # Fecha (Fallback a la fecha de salida del itinerario si falta en el segmento)
            if not f.get('departureDate'):
                f['departureDate'] = meta.get('outboundDate', 'Por confirmar')

            clean_flights.append(f)
        meta['flights'] = clean_flights
        
        # 4. Asegurar que la agencia esté disponible para el branding (Incluso para anónimos)
        if not context.get('current_agency'):
            try:
                from core.models.agencia import UsuarioAgencia
                ua = UsuarioAgencia.objects.filter(usuario=quote.consultor, activo=True).first()
                if ua:
                    context['current_agency'] = ua.agencia
            except Exception:
                pass

        # 5. Forzar actualización de imagen si el destino era genérico
        if 'unsplash' not in meta.get('image', '').lower() and 'Varios' not in meta['destination']:
             # Solo si no tiene una imagen de Unsplash ya puesta
             search = meta.get('image_search_query') or meta['destination']
             meta['image_search_query'] = search

        quote.metadata_ia = meta
        return context
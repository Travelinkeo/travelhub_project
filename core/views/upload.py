import logging
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from apps.bookings.models import BoletoImportado, Venta, ItemVenta
from apps.crm.models import Cliente

logger = logging.getLogger(__name__)

class SafeDict(dict):
    """
    Evita errores 500 de VariableDoesNotExist en los templates de Django 
    cuando faltan llaves en el JSON de la IA.
    """
    def __getitem__(self, key):
        # Si la llave no existe, devuelve vacío en lugar de explotar (KeyError)
        return super().get(key, '')
        
    def __getattr__(self, key):
        return super().get(key, '')

class UploadBoletoView(View):
    def post(self, request, *args, **kwargs):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return HttpResponse('<div class="text-red-400 text-sm">Error: Falta archivo</div>', status=400)
        
        try:
            # 1. Guardar el boleto inicial
            agencia = getattr(request, 'agencia', None)
            if not agencia and request.user.is_authenticated:
                ua = request.user.agencias.filter(activo=True).first()
                if ua: agencia = ua.agencia

            boleto = BoletoImportado.objects.create(
                archivo_boleto=archivo,
                agencia=agencia, 
                estado_parseo='PEN'
            )

            # 2. Procesamiento Síncrono Usando el Servicio Central (IA habilitada)
            from core.services.ticket_parser_service import TicketParserService
            from django.urls import reverse
            
            servicio = TicketParserService()
            resultado = servicio.procesar_boleto(boleto.pk)
            
            if resultado: 
                # SIEMPRE redirigir al Review Master para validación humana (Fase 4.0)
                review_url = reverse('core:revisar_boleto', kwargs={'pk': boleto.pk})
                response = HttpResponse()
                response['HX-Redirect'] = review_url
                return response
            else:
                boleto.refresh_from_db()
                error_msg = boleto.log_parseo or "No se pudo extraer información válida."
                raise Exception(error_msg)

        except Exception as e:
            # Si falla el procesado síncrono, mostramos error
            return HttpResponse(f'<div class="fixed bottom-5 right-5 bg-red-900 border-l-4 border-red-500 text-white p-4 rounded shadow-xl animate-bounce-in">Error procesando boleto: {str(e)}</div>', status=200)

class ReviewBoletoView(View):
    template_name = 'core/tickets/review_master.html'
    
    def get(self, request, pk, *args, **kwargs):
        from apps.crm.models import Cliente
        from django.views.decorators.cache import patch_cache_control
        
        try:
            boleto = BoletoImportado.objects.get(pk=pk)
        except BoletoImportado.DoesNotExist:
            return HttpResponse("Boleto no encontrado", status=404)
            
        next_url = request.GET.get('next')
        clientes = Cliente.objects.all().order_by('apellidos', 'nombres')
        
        # Asegurar que el texto original esté disponible para el panel de "Fuente"
        source_text = boleto.log_parseo or ""
        # Si el log parece corto (solo logs de error) o está vacío, intentamos extraer el texto real
        if len(source_text) < 100 or "Itinerario" not in source_text:
            from core.services.ticket_parser_service import TicketParserService
            servicio = TicketParserService()
            texto_extraido = servicio._extraer_texto(boleto)
            if texto_extraido:
                source_text = texto_extraido
                # No guardamos en DB para no ensuciar logs permanentes, solo pasamos al contexto
        
        # --- FIX DE SEGURIDAD PARA DJANGO TEMPLATES ---
        if boleto.datos_parseados is None:
            boleto.datos_parseados = SafeDict()
        elif isinstance(boleto.datos_parseados, dict):
            # 🛡️ PUENTE DE TRADUCCIÓN (Rosetta Stone):
            # Unificamos las llaves del nuevo God Mode con las llaves que espera el HTML
            datos = boleto.datos_parseados
            datos['passenger_name'] = datos.get('NOMBRE_DEL_PASAJERO') or datos.get('passenger_name', '')
            datos['passenger_document'] = datos.get('CODIGO_IDENTIFICACION') or datos.get('passenger_document', '')
            datos['pnr'] = datos.get('CODIGO_RESERVA') or datos.get('SOLO_CODIGO_RESERVA') or datos.get('pnr', '')
            datos['ticket_number'] = datos.get('NUMERO_DE_BOLETO') or datos.get('ticket_number', '')
            datos['aerolinea'] = datos.get('NOMBRE_AEROLINEA') or datos.get('aerolinea', '')
            datos['fecha_emision'] = datos.get('FECHA_DE_EMISION') or datos.get('fecha_emision', '')
            
            # Sincronización de itinerarios: IA vs Legacy
            datos['segments'] = datos.get('segmentos') or datos.get('itinerario') or datos.get('flights')
            datos['segmentos'] = datos['segments']
            datos['itinerario'] = datos['segments']
            
            boleto.datos_parseados = SafeDict(datos)
        # ----------------------------------------------
            
        # Extraer segmentos para la iteración dinámica en el template
        datos = boleto.datos_parseados
        # Sincronización AI: La IA entrega 'itinerario', el service traduce a 'segmentos'
        segments = datos.get('flights', []) or datos.get('itinerario', []) or datos.get('segments', []) or datos.get('vuelos', []) or datos.get('segmentos', [])
        
        response = render(request, self.template_name, {
            'boleto': boleto, 
            'source_text': source_text,
            'segments': segments,
            'clientes_disponibles': clientes,
            'next_url': next_url,
            'csp_nonce': getattr(request, 'csp_nonce', ''),
        })
        
        # 🛡️ ANTI-CACHE GLOBAL (Browser, Cloudflare, Nginx)
        from django.views.decorators.cache import patch_cache_control
        patch_cache_control(response, no_cache=True, no_store=True, must_revalidate=True, max_age=0)
        return response
    
    def post(self, request, pk, *args, **kwargs):
        try:
            from decimal import Decimal
            next_url = request.GET.get('next') or request.POST.get('next')
            boleto = BoletoImportado.objects.get(pk=pk)
            
            # 1. Recolección de datos del formulario (AI Studio)
            nombre = request.POST.get('nombre_pasajero')
            foid = request.POST.get('foid_pasajero')
            cliente_id = request.POST.get('cliente_id')
            pnr = request.POST.get('localizador_pnr')
            ticket_no = request.POST.get('ticket_number')
            fare = request.POST.get('fare_amount', '0')
            taxes = request.POST.get('taxes_amount', '0')
            total = request.POST.get('total_amount', '0')
            total_currency = request.POST.get('total_currency', 'USD')
            
            # 2. Actualizar campos directos del modelo
            if foid: boleto.foid_pasajero = foid
            if nombre:
                boleto.nombre_pasajero_procesado = nombre
                boleto.nombre_pasajero_completo = nombre
            if pnr: boleto.localizador_pnr = pnr
            if ticket_no: boleto.numero_boleto = ticket_no
            
            try:
                boleto.tarifa_base = Decimal(fare.replace(',', ''))
                boleto.otros_impuestos_monto = Decimal(taxes.replace(',', ''))
                boleto.total_boleto = Decimal(total.replace(',', ''))
            except: pass
            
            # 3. Mergear con datos_parseados (Persistence fix)
            datos = boleto.datos_parseados or {}
            datos.update({
                'passenger_name': nombre,
                'passenger_document': foid,
                'pnr': pnr,
                'ticket_number': ticket_no,
                'total_amount': total,
                'total_currency': total_currency,
                'fare_amount': fare,
                'tax_details': taxes,
                
                # 🛡️ Sincronizar también las llaves nuevas del God Mode para el VentaBuilder
                'NOMBRE_DEL_PASAJERO': nombre,
                'CODIGO_IDENTIFICACION': foid,
                'CODIGO_RESERVA': pnr,
                'NUMERO_DE_BOLETO': ticket_no,
                'TARIFA': fare,
                'IMPUESTOS': taxes,
                'TOTAL': total,
                'TOTAL_MONEDA': total_currency,
            })
            boleto.datos_parseados = datos
            
            if cliente_id:
                request.session['forced_cliente_id'] = cliente_id
            
            boleto.log_parseo = (boleto.log_parseo or "") + "\n✅ Datos actualizados manualmente vía Studio."
            boleto.save()
            
            # 4. Reintentar procesamiento usando el servicio central
            from core.services.ticket_parser_service import TicketParserService
            from django.urls import reverse
            
            servicio = TicketParserService()
            # Pasamos el cliente forzado si existe
            venta = servicio.procesar_boleto(boleto.pk, forced_client_id=cliente_id)
            
            # Refrescar para verificar éxito
            boleto.refresh_from_db()
            if boleto.estado_parseo == 'COM' and boleto.venta_asociada:
                venta = boleto.venta_asociada
            
            if isinstance(venta, Venta):
                # Éxito Final - Redirigir a la edición de la venta
                edit_url = reverse('core:editar_venta', kwargs={'pk': venta.pk})
                if next_url:
                    edit_url += f"?next={next_url}"
                
                response = HttpResponse()
                response['HX-Redirect'] = edit_url
                return response
            else:
                 error_msg = boleto.log_parseo or "Error desconocido al reprocesar."
                 return HttpResponse(f'<div class="bg-red-900/50 p-4 rounded-xl border border-red-500/30 text-white font-bold">Error: {error_msg}</div>', status=200)

        except Exception as e:
            import traceback
            logger.error(f"Error en ReviewBoletoView: {e}\n{traceback.format_exc()}")
            return HttpResponse(f'<div class="bg-red-900/50 p-4 rounded-xl border border-red-500/30 text-white font-bold">Error crítico: {str(e)}</div>', status=200)
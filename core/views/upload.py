import logging
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
        
        # --- LÓGICA DE RE-PARSEO (FORCE) ---
        force = request.GET.get('force') == '1'
        if force or not boleto.datos_parseados or (isinstance(boleto.datos_parseados, dict) and not boleto.datos_parseados.get('passenger_name')):
            from core.services.ticket_parser_service import TicketParserService
            servicio = TicketParserService()
            # Forzamos ignorar manual y bypass_cache para que corra el motor de nuevo e ignore la caché
            servicio.procesar_boleto(boleto.pk, ignore_manual=True, bypass_cache=True)
            boleto.refresh_from_db()

        # Asegurar que el texto original esté disponible para el panel de "Fuente"
        from core.services.ticket_parser_service import TicketParserService
        try:
            source_text = TicketParserService()._extraer_texto(boleto) or boleto.log_parseo or "No se pudo extraer texto del archivo."
        except:
            source_text = boleto.log_parseo or "Error al leer el archivo fuente."
        
        # --- FIX DE SEGURIDAD PARA DJANGO TEMPLATES ---
        if boleto.datos_parseados is None:
            boleto.datos_parseados = {}
        
        if isinstance(boleto.datos_parseados, dict):
            # 🛡️ PUENTE DE TRADUCCIÓN (Rosetta Stone):
            # Unificamos las llaves del nuevo God Mode con las llaves que espera el HTML
            # Usamos SafeDict para evitar VariableDoesNotExist en el template
            datos = SafeDict(boleto.datos_parseados or {})
            
            # 🩹 REPARACIÓN AGRESIVA: Si faltan datos clave (PNR o Segmentos)
            # Intentamos usar el motor de Regex más reciente sobre el texto fuente.
            if not datos.get('codigo_reserva') and not datos.get('pnr') and not datos.get('CODIGO_RESERVA'):
                from core.ticket_parser import FastDeterministicParsers
                latest_regex = FastDeterministicParsers.parse_general_regex(source_text)
                
                if latest_regex.get('codigo_reserva'):
                    datos['codigo_reserva'] = latest_regex['codigo_reserva']
                    datos['CODIGO_RESERVA'] = latest_regex['codigo_reserva']
                
                if latest_regex.get('flights'):
                    datos['flights'] = latest_regex['flights']
                    datos['segmentos'] = latest_regex['flights']
            
            # Sincronización Bidireccional: Aseguramos que existan tanto las llaves legacy como las nuevas
            datos['NOMBRE_DEL_PASAJERO'] = datos.get('NOMBRE_DEL_PASAJERO') or datos.get('passenger_name') or datos.get('nombre_pasajero', '')
            datos['CODIGO_IDENTIFICACION'] = datos.get('CODIGO_IDENTIFICACION') or datos.get('passenger_document') or datos.get('foid', '')
            datos['CODIGO_RESERVA'] = datos.get('CODIGO_RESERVA') or datos.get('SOLO_CODIGO_RESERVA') or datos.get('pnr', '')
            datos['NUMERO_DE_BOLETO'] = datos.get('NUMERO_DE_BOLETO') or datos.get('ticket_number') or datos.get('numero_boleto', '')
            datos['NOMBRE_AEROLINEA'] = datos.get('NOMBRE_AEROLINEA') or datos.get('aerolinea') or datos.get('aerolinea_emisora', '')
            datos['FECHA_DE_EMISION'] = datos.get('FECHA_DE_EMISION') or datos.get('fecha_emision', '')
            
            # Mapeo inverso para consistencia
            datos['passenger_name'] = datos['NOMBRE_DEL_PASAJERO']
            datos['passenger_document'] = datos['CODIGO_IDENTIFICACION']
            datos['pnr'] = datos['CODIGO_RESERVA']
            datos['ticket_number'] = datos['NUMERO_DE_BOLETO']
            datos['aerolinea'] = datos['NOMBRE_AEROLINEA']
            
            # Sincronización de itinerarios: IA vs Legacy
            itinerary_data = datos.get('segmentos', []) or datos.get('flights', []) or datos.get('itinerario', []) or datos.get('segments', []) or datos.get('vuelos', [])
            
            # Normalización rápida para el UI (Review Master)
            normalized_segments = []
            for tramo in itinerary_data:
                if not isinstance(tramo, dict): continue
                # Si el tramo viene con estructura anidada (Gemini), lo aplanamos para el template
                dep = tramo.get('departure', {}) if isinstance(tramo.get('departure'), dict) else {}
                arr = tramo.get('arrival', {}) if isinstance(tramo.get('arrival'), dict) else {}
                
                normalized_segments.append({
                    'origen': tramo.get('origen') or dep.get('location') or tramo.get('departure_city'),
                    'destino': tramo.get('destino') or arr.get('location') or tramo.get('arrival_city'),
                    'vuelo': tramo.get('vuelo') or tramo.get('flightNumber') or tramo.get('numero_vuelo') or tramo.get('flight_number'),
                    'fecha_salida': tramo.get('fecha_salida') or tramo.get('date') or tramo.get('departure_date') or tramo.get('date'),
                    'hora_salida': tramo.get('hora_salida') or dep.get('time'),
                    'hora_llegada': tramo.get('hora_llegada') or arr.get('time'),
                })
            
            # Bubble up Airline PNR from first segment if missing
            if not datos.get('pnr_aerolinea') or datos.get('pnr_aerolinea') == '---':
                for seg in normalized_segments:
                    if seg.get('airline_pnr'):
                        datos['pnr_aerolinea'] = seg['airline_pnr']
                        break

            datos['segmentos'] = normalized_segments
            datos['segments'] = normalized_segments
            boleto.datos_parseados = datos
        # ----------------------------------------------
            
        segments = boleto.datos_parseados.get('segmentos', [])
        
        agencia = getattr(request, 'agencia', None)
        
        response = render(request, self.template_name, {
            'boleto': boleto,
            'parsed_data': datos,
            'segments': segments,
            'agencia': agencia,
            'clientes': Cliente.objects.filter(agencia=agencia).order_by('nombres') if agencia else [],
            'error_ia': datos.get('error_ia'),
            'source_text': source_text,
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
            pnr_aerolinea = request.POST.get('pnr_aerolinea')
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
                'pnr_aerolinea': pnr_aerolinea,
                'airline_pnr': pnr_aerolinea,
                'ticket_number': ticket_no,
                'total_amount': total,
                'total_currency': total_currency,
                'fare_amount': fare,
                'tax_details': taxes,
                
                # 🛡️ Sincronizar también las llaves nuevas del God Mode para el VentaBuilder
                'NOMBRE_DEL_PASAJERO': nombre,
                'CODIGO_IDENTIFICACION': foid,
                'CODIGO_RESERVA': pnr,
                'CODIGO_RESERVA_AEROLINEA': pnr_aerolinea,
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
            # 🛡️ FIX CRÍTICO: Usamos manual_only=True para que NO vuelva a correr la IA 
            # y respete los montos que el usuario acaba de escribir.
            venta = servicio.procesar_boleto(boleto.pk, forced_client_id=cliente_id, manual_only=True)
            
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

class DesasociarVentaView(View):
    """
    Desasocia un boleto de su venta actual para permitir un re-parseo limpio.
    """
    def post(self, request, pk):
        boleto = get_object_or_404(BoletoImportado, pk=pk)
        
        if boleto.venta_asociada:
            venta = boleto.venta_asociada
            # 1. Desvincular
            boleto.venta_asociada = None
            # 2. Resetear estado para permitir re-proceso
            boleto.estado_parseo = 'PEN'
            boleto.save()
            
            # 3. Informar
            messages.info(request, f"Boleto desasociado de la venta {venta.localizador}. El boleto está listo para re-procesarse.")
        
        return redirect('core:revisar_boleto', pk=pk)

@login_required
def eliminar_boleto(request, pk):
    """🗑️ Eliminación física de un boleto y sus archivos."""
    
    # Obtener el boleto con all_objects para asegurar que lo encontramos
    boleto = get_object_or_404(BoletoImportado.all_objects, pk=pk)
    
    # Seguridad: Solo la misma agencia
    if not request.user.is_superuser and hasattr(request, 'agencia'):
        if boleto.agencia != request.agencia:
            messages.error(request, "No tiene permisos para eliminar este boleto.")
            return redirect('core:boletos_importar')

    try:
        # Borrar archivos físicos
        if boleto.archivo_boleto:
            boleto.archivo_boleto.delete(save=False)
        if boleto.archivo_pdf_generado:
            try:
                boleto.archivo_pdf_generado.delete(save=False)
            except: pass
        
        # Borrar registro físico
        boleto.delete(force=True)
        
        messages.success(request, "Boleto eliminado físicamente con éxito.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {str(e)}")
        
    return redirect(request.GET.get('next') or 'core:boletos_importar')
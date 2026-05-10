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

            # 2. Procesamiento Asíncrono (Celery)
            from ..tasks import parsear_boleto_individual
            from ..utils.celery_utils import safe_delay
            from django.urls import reverse
            
            # Encolar la tarea
            safe_delay(parsear_boleto_individual, boleto.pk)
            
            # Redirigir INMEDIATAMENTE al Review Master
            # El Review Master se encargará de mostrar el spinner si sigue procesando
            review_url = reverse('core:revisar_boleto', kwargs={'pk': boleto.pk})
            response = HttpResponse()
            response['HX-Redirect'] = review_url
            return response

        except Exception as e:
            logger.exception(f"Error en subida de boleto: {e}")
            return HttpResponse(f'<div class="fixed bottom-5 right-5 bg-red-900 border-l-4 border-red-500 text-white p-4 rounded shadow-xl animate-bounce-in">Error al recibir boleto: {str(e)}</div>', status=200)

class ReviewBoletoView(View):
    template_name = 'core/tickets/review_master.html'
    
    def get(self, request, pk, *args, **kwargs):
        from apps.crm.models import Cliente
        from django.views.decorators.cache import patch_cache_control
        
        try:
            boleto = BoletoImportado.all_objects.get(pk=pk)
        except BoletoImportado.DoesNotExist:
            return HttpResponse("Boleto no encontrado", status=404)
            
        # Seguridad multi-tenant
        agencia = getattr(request, 'agencia', None)
        if not request.user.is_superuser and boleto.agencia != agencia:
            return HttpResponse("No tiene permisos para ver este boleto", status=403)
            
        next_url = request.GET.get('next')
        clientes = Cliente.objects.all().order_by('apellidos', 'nombres')
        
        # --- LÓGICA DE RE-PARSEO (ASYNC) ---
        force = request.GET.get('force') == '1'
        is_processing = boleto.estado_parseo in ['PRO', 'QUE']
        
        if force:
            from ..tasks import parsear_boleto_individual
            from ..utils.celery_utils import safe_delay
            # Resetear estado y encolar
            boleto.estado_parseo = 'PRO'
            boleto.log_parseo = "Re-procesamiento solicitado manualmente."
            boleto.save(update_fields=['estado_parseo', 'log_parseo'])
            safe_delay(parsear_boleto_individual, boleto.pk)
            is_processing = True
        
        if is_processing:
            # Si se solicita via HTMX, devolvemos solo el fragmento del spinner o el contenido final
            # Pero para simplificar, el template manejará el polling
            pass
        elif not boleto.datos_parseados or (isinstance(boleto.datos_parseados, dict) and not boleto.datos_parseados.get('passenger_name')):
             # Auto-reintento si faltan datos y no está procesando
             from ..tasks import parsear_boleto_individual
             from ..utils.celery_utils import safe_delay
             boleto.estado_parseo = 'PRO'
             boleto.save(update_fields=['estado_parseo'])
             safe_delay(parsear_boleto_individual, boleto.pk)
             is_processing = True

        # Asegurar que el texto original esté disponible para el panel de "Fuente"
        from core.services.ticket_parser_service import TicketParserService
        try:
            source_text = TicketParserService()._extraer_texto(boleto) or boleto.log_parseo or "No se pudo extraer texto del archivo."
        except:
            source_text = boleto.log_parseo or "Error al leer el archivo fuente."
        
        # --- NORMALIZACIÓN DE DATOS PARA EL UI (Studio) ---
        from core.services.parsers.normalization import DataNormalizationService
        datos_crudos = boleto.datos_parseados or {}
        datos_norm = DataNormalizationService.normalize_ticket_data(datos_crudos)
        datos = SafeDict(datos_norm)
        
        if not datos.get('pnr') and not is_processing:
            from core.ticket_parser import FastDeterministicParsers
            regex_emergency = FastDeterministicParsers.parse_general_regex(source_text)
            if regex_emergency.get('codigo_reserva'):
                datos.update(DataNormalizationService.normalize_ticket_data(regex_emergency))
            


            
        segments = datos.get('segmentos', [])
        boleto.datos_parseados = datos
        # ----------------------------------------------
            
        segments = boleto.datos_parseados.get('segmentos', [])
        
        agencia = getattr(request, 'agencia', None)
        
        response = render(request, self.template_name, {
            'boleto': boleto,
            'parsed_data': datos,
            'segments': segments,
            'agencia': agencia,
            'clientes': Cliente.objects.filter(agencia=agencia).order_by('apellidos', 'nombres') if agencia else [],
            'is_processing': is_processing,
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
            boleto = BoletoImportado.all_objects.get(pk=pk)
            
            # Seguridad multi-tenant
            agencia = getattr(request, 'agencia', None)
            if not request.user.is_superuser and boleto.agencia != agencia:
                return HttpResponse("No tiene permisos para modificar este boleto", status=403)
                
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
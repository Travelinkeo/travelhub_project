from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
# from core.parsers.kiu_parser import KIUParser 
# from core.services.venta_automation import VentaAutomationService
from django.utils import timezone
from core.models import BoletoImportado, Venta, ItemVenta, Cliente

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
            
            if isinstance(resultado, dict) and resultado.get('status') == 'REVIEW_REQUIRED':
                review_url = reverse('core:revisar_boleto', kwargs={'pk': resultado['boleto_id']})
                response = HttpResponse()
                response['HX-Redirect'] = review_url
                return response

            if resultado: # Si resultado es un objeto Venta (Éxito)
                edit_url = reverse('core:editar_venta', kwargs={'pk': resultado.id})
                response = HttpResponse()
                response['HX-Redirect'] = edit_url
                return response
            else:
                boleto.refresh_from_db()
                error_msg = boleto.log_parseo or "No se pudo extraer información válida."
                raise Exception(error_msg)

        except Exception as e:
            # Si falla el procesado síncrono, mostramos error
            return HttpResponse(f'<div class="fixed bottom-5 right-5 bg-red-900 border-l-4 border-red-500 text-white p-4 rounded shadow-xl animate-bounce-in">Error procesando boleto: {str(e)}</div>', status=200)

class ReviewBoletoView(View):
    template_name = 'core/tickets/review_boleto_v2.html'
    
    def get(self, request, pk, *args, **kwargs):
        boleto = BoletoImportado.objects.get(pk=pk)
        next_url = request.GET.get('next')
        clientes = Cliente.objects.all().order_by('apellidos', 'nombres')
        return render(request, self.template_name, {
            'boleto': boleto, 
            'next': next_url,
            'clientes_disponibles': clientes
        })
    
    def post(self, request, pk, *args, **kwargs):
        try:
            next_url = request.GET.get('next') or request.POST.get('next')
            boleto = BoletoImportado.objects.get(pk=pk)
            foid = request.POST.get('foid_pasajero')
            nombre = request.POST.get('nombre_pasajero')
            cliente_id = request.POST.get('cliente_id')
            
            updated = False
            if foid:
                boleto.foid_pasajero = foid
                updated = True
            
            if nombre:
                boleto.nombre_pasajero_procesado = nombre
                boleto.nombre_pasajero_completo = nombre
                updated = True
                
            if cliente_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id)
                    # We store it in metadata or wait for the service to handle it
                    # For now, let's just make sure it's available for the parser service
                    # The service usually looks for a matched client, so we might need
                    # to force it or set a field in BoletoImportado if it existed.
                    # Since it doesn't, we can pass it via session or context if needed.
                    # Actually, the best way is to improve TicketParserService to accept forced data.
                    request.session['forced_cliente_id'] = cliente_id
                except Cliente.DoesNotExist:
                    pass
                
            if updated:
                # Importante: Actualizamos el log para quitar el mensaje de espera
                boleto.log_parseo = (boleto.log_parseo or "") + "\n✅ Datos ingresados manualmente."
                boleto.save()
            
            
            # Reintentar procesamiento
            from core.services.ticket_parser_service import TicketParserService
            from django.urls import reverse
            
            servicio = TicketParserService()
            venta = servicio.procesar_boleto(boleto.pk)
            
            # Verificar estado del boleto ACTUAL
            boleto.refresh_from_db()
            if boleto.estado_parseo == 'COM' and boleto.venta_asociada:
                # El boleto actual se procesó bien.
                venta = boleto.venta_asociada
            else:
                 # Si no se completó, miramos si devolvió status de revisión
                 if isinstance(venta, dict) and venta.get('status') == 'REVIEW_REQUIRED':
                      # Si el ID devuelto es EL MISMO boleto, es error.
                      # Si es otro, es chaining (pero aquí deberíamos haber detectado éxito del actual)
                      if str(venta.get('boleto_id')) == str(pk):
                          return HttpResponse('<div class="bg-red-100 p-3 rounded">Error: Sigue faltando información para este boleto.</div>', status=200)

            if venta and isinstance(venta, Venta):
                # Verificar si hay otros boletos HERMANOS (mismo archivo) en estado 'REV'
                siguiente_revision = BoletoImportado.objects.filter(
                    archivo_boleto=boleto.archivo_boleto, 
                    estado_parseo='REV'
                ).exclude(pk=boleto.pk).first()

                if siguiente_revision:
                     # Redirigir al siguiente boleto pendiente
                    review_url = reverse('core:revisar_boleto', kwargs={'pk': siguiente_revision.pk})
                    response = HttpResponse()
                    response['HX-Redirect'] = review_url
                    return response

                # Éxito Final - Redirigir a la edición
                # Validamos que venta sea un objeto con ID (por si acaso)
                venta_id = getattr(venta, 'id', None) or getattr(venta, 'pk', None)
                # Éxito Final - Redirigir a la edición
                # Validamos que venta sea un objeto con ID (por si acaso)
                venta_id = getattr(venta, 'id', None) or getattr(venta, 'pk', None)
                if venta_id:
                    edit_url = reverse('core:editar_venta', kwargs={'pk': venta_id})
                    if next_url:
                        edit_url += f"?next={next_url}"
                    
                    response = HttpResponse()
                    response['HX-Redirect'] = edit_url
                    return response
                else:
                     return HttpResponse('<div class="bg-red-100 p-3 rounded">Error: Venta creada sin ID válido.</div>', status=200)
            else:
                 error_msg = boleto.log_parseo or "Error desconocido al reprocesar."
                 return HttpResponse(f'<div class="bg-red-100 p-3 rounded">Error: {error_msg}</div>', status=200)

        except Exception as e:
            return HttpResponse(f'<div class="bg-red-100 p-3 rounded">Error crítico: {str(e)}</div>', status=200)

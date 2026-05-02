from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class CotizacionMagicQuoterPageView(LoginRequiredMixin, TemplateView):
    template_name = 'core/erp/cotizaciones/magic_quoter.html'

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
            from apps.contabilidad.models import TasaCambioBCV
            tasa = TasaCambioBCV.objects.latest('fecha')
            context['tasa_bcv'] = float(tasa.tasa_bsd_por_usd)
        except Exception:
            context['tasa_bcv'] = 0
            
        return context
from django.db.models import Q
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction

from apps.cotizaciones.models import Cotizacion
from core.forms import CotizacionForm, ItemCotizacionFormSet

class CotizacionDashboardView(LoginRequiredMixin, ListView):
    model = Cotizacion
    template_name = 'core/erp/cotizaciones/dashboard.html'
    context_object_name = 'cotizaciones'
    paginate_by = 20

    def get_queryset(self):
        queryset = Cotizacion.objects.select_related('cliente', 'moneda').order_by('-fecha_emision')
        
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(numero_cotizacion__icontains=q) |
                Q(cliente__nombres__icontains=q) |
                Q(cliente__apellidos__icontains=q) |
                Q(cliente__numero_documento__icontains=q)
            )
            
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Stats
        context['total_cotizaciones'] = Cotizacion.objects.count()
        context['cotizaciones_pendientes'] = Cotizacion.objects.filter(estado='BOR').count() # Borrador as pending
        context['cotizaciones_enviadas'] = Cotizacion.objects.filter(estado='ENV').count()
        return context

class CotizacionDetailView(LoginRequiredMixin, DetailView):
    model = Cotizacion
    template_name = 'core/erp/cotizaciones/detalle.html'
    context_object_name = 'cotizacion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items_cotizacion.all()
        return context

class CotizacionCreateView(LoginRequiredMixin, CreateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'core/erp/cotizaciones/crear_cotizacion_swiss.html'
    success_url = reverse_lazy('core:cotizacion_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = ItemCotizacionFormSet(self.request.POST)
        else:
            context['items_formset'] = ItemCotizacionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        with transaction.atomic():
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, f"Cotización {self.object.numero_cotizacion} creada exitosamente.")
        return super().form_valid(form)

class CotizacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'core/erp/cotizaciones/crear_cotizacion_swiss.html'
    
    def get_success_url(self):
        return reverse_lazy('core:cotizacion_detalle', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = ItemCotizacionFormSet(self.request.POST, instance=self.object)
        else:
            context['items_formset'] = ItemCotizacionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        with transaction.atomic():
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, f"Cotización {self.object.numero_cotizacion} actualizada exitosamente.")
        return super().form_valid(form)

from django.views import View
from django.shortcuts import get_object_or_404

class CotizacionStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        nuevo_estado = request.POST.get('nuevo_estado')
        
        # Validar transiciones permitidas
        permitido = False
        if cotizacion.estado == Cotizacion.EstadoCotizacion.BORRADOR and nuevo_estado == Cotizacion.EstadoCotizacion.ENVIADA:
            permitido = True
        elif cotizacion.estado == Cotizacion.EstadoCotizacion.ENVIADA and nuevo_estado in [Cotizacion.EstadoCotizacion.ACEPTADA, Cotizacion.EstadoCotizacion.RECHAZADA]:
            permitido = True
        elif cotizacion.estado == Cotizacion.EstadoCotizacion.RECHAZADA and nuevo_estado == Cotizacion.EstadoCotizacion.BORRADOR:
            # Opción para reabrir/restaurar
            permitido = True
            
        if permitido:
            cotizacion.estado = nuevo_estado
            cotizacion.save()
            messages.success(request, f"Estado actualizado a {cotizacion.get_estado_display()}.")
        else:
            messages.error(request, "Cambio de estado no permitido.")
            
        return redirect('core:cotizacion_detalle', pk=pk)

class CotizacionPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        try:
             # Importar servicio aquí para evitar ciclos si los hubiera
            from apps.cotizaciones.pdf_service import generar_pdf_cotizacion
            pdf_bytes = generar_pdf_cotizacion(cotizacion)
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            filename = f"Cotizacion_{cotizacion.numero_cotizacion}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            messages.error(request, f"Error generando PDF: {str(e)}")
            return redirect('core:cotizacion_detalle', pk=pk)

class CotizacionConvertirView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        
        try:
            with transaction.atomic():
                venta = cotizacion.convertir_a_venta()
                messages.success(request, f"Venta generada exitosamente: {venta.localizador}")
                return redirect('core:venta_detalle', pk=venta.pk)
        except ValueError as e:
            messages.warning(request, str(e))
        except Exception as e:
            messages.error(request, f"Error al convertir a venta: {str(e)}")
            
        return redirect('core:cotizacion_detalle', pk=pk)

from django.shortcuts import render

class CotizacionHTMXCalculateTotalsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        subtotal = 0
        impuestos = 0
        total = 0
        
        # Iterate over formset data to calculate totals
        total_forms = int(request.POST.get('items_cotizacion-TOTAL_FORMS', 0))
        for i in range(total_forms):
            delete_key = f'items_cotizacion-{i}-DELETE'
            delete_val = request.POST.get(delete_key)
            if delete_val == 'on' or delete_val == 'true':
                continue
                
            qty_str = request.POST.get(f'items_cotizacion-{i}-cantidad', '0')
            price_str = request.POST.get(f'items_cotizacion-{i}-precio_unitario', '0')
            tax_str = request.POST.get(f'items_cotizacion-{i}-impuestos_item', '0')
            
            try:
                qty = float(qty_str) if qty_str else 0
                price = float(price_str) if price_str else 0
                tax = float(tax_str) if tax_str else 0
                
                subtotal += (qty * price)
                impuestos += (qty * tax)
            except ValueError:
                pass
                
        total = subtotal + impuestos
        
        moneda_id = request.POST.get('moneda')
        moneda_symbol = "$"
        if moneda_id:
            from core.models_catalogos import Moneda
            try:
                moneda = Moneda.objects.get(pk=moneda_id)
                moneda_symbol = moneda.simbolo or moneda.codigo_iso
            except Exception:
                pass
                
        # Pasamos el PK de la instancia si existe, solo visual
        instance_pk = kwargs.get('pk') or request.POST.get('cotizacion_id')

        return render(request, 'core/erp/cotizaciones/partials/_summary.html', {
            'subtotal': subtotal,
            'impuestos': impuestos,
            'total': total,
            'moneda_symbol': moneda_symbol,
            'instance_pk': instance_pk
        })

from django.http import JsonResponse
from core.services.ai_engine import ai_engine
from core.services.sales_intelligence_service import SalesIntelligenceService

class CotizacionMagicGPTView(LoginRequiredMixin, View):
    """
    Magic Quoter: Transforma texto de GDS en una Cotización Estructurada con IA.
    """
    def post(self, request):
        raw_text = request.POST.get('raw_text')
        if not raw_text:
            return JsonResponse({'success': False, 'error': 'No se proporcionó texto de GDS'})

        try:
            # 1. Parsear con IA
            parsed_data = ai_engine.analyze_gds_terminal(raw_text)
            
            # ResultadoParseoSchema devuelve una lista de 'boletos'
            boletos = parsed_data.get('boletos', [])
            if not boletos:
                return JsonResponse({'success': False, 'error': 'No se pudo detectar información de boletos en el texto.'})
            
            primer_boleto = boletos[0]
            itinerario = primer_boleto.get('itinerario', [])
            
            if not itinerario:
                return JsonResponse({'success': False, 'error': 'No se pudo detectar el itinerario dentro del boleto.'})

            # 2. Buscar imagen de destino (Concepto)
            destino_final = itinerario[-1].get('destino_ciudad', 'Viajes')
            image_prompt = f"travel destination {destino_final} landscape high quality"
            # TODO: Integrar aquí búsqueda real en Unsplash o similar. Por ahora simular URL.
            image_url = f"https://source.unsplash.com/featured/?{destino_final.replace(' ', '')},travel"

            # 3. Crear Cotización (Borrador)
            ua = request.user.agencias.filter(activo=True).first()
            agencia = ua.agencia if ua else None
            
            with transaction.atomic():
                cotizacion = Cotizacion.objects.create(
                    consultor=request.user,
                    descripcion_general=f"Cotización rápida para {destino_final}",
                    destino=destino_final,
                    total_cotizado=primer_boleto.get('total', 0),
                    gds_raw_text=raw_text,
                    image_url=image_url,
                    # metadata_ia=parsed_data # Desactivado temporalmente si el campo no existe en el DB real aún
                )
                
                # 4. Crear Items de Cotización (Vuelos)
                from apps.cotizaciones.models import ItemCotizacion
                for seg in itinerario:
                    ItemCotizacion.objects.create(
                        cotizacion=cotizacion,
                        tipo_item=ItemCotizacion.TipoItem.VUELO,
                        descripcion=f"Vuelo {seg.get('aerolinea')} {seg.get('numero_vuelo')}: {seg.get('origen_iata')} -> {seg.get('destino_iata')}",
                        precio_unitario=primer_boleto.get('tarifa', 0) / len(itinerario) if len(itinerario) > 0 else 0,
                        cantidad=1,
                        total_item=primer_boleto.get('total', 0) / len(itinerario) if len(itinerario) > 0 else 0
                    )

            return JsonResponse({
                'success': True, 
                'redirect_url': reverse_lazy('core:cotizacion_detalle', kwargs={'pk': cotizacion.pk}),
                'message': f"Cotización {cotizacion.numero_cotizacion} generada exitosamente!"
            })

        except Exception as e:
            import traceback
            logger.error(f"Error en Magic Quoter: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e)})

class CotizacionHTMXAddItemView(LoginRequiredMixin, View):
    # (Existing implementation kept)
    def get(self, request, *args, **kwargs):
        index = int(request.GET.get('index', 0))
        formset = ItemCotizacionFormSet()
        empty_form = formset.empty_form
        empty_form.prefix = f'items_cotizacion-{index}'
        
        return render(request, 'core/erp/cotizaciones/partials/_item_row_with_oob.html', {
            'form': empty_form,
            'index': index,
            'next_index': index + 1
        })


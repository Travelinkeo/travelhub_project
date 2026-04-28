import json
import logging
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.crm.models import Cliente
from apps.bookings.models import BoletoImportado, Venta
from core.services.parsers.venta_builder import VentaBuilderService
from core.services.ai_engine import AIEngine

logger = logging.getLogger(__name__)

class GDSAnalyzerView(LoginRequiredMixin, TemplateView):
    template_name = 'core/intelligence/gds_intelligence.html'

class GDSAnalysisAjaxView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            terminal_text = request.POST.get('terminal_text')
            gds_type = request.POST.get('gds_type', 'SABRE')
            
            if not terminal_text:
                return JsonResponse({'status': 'error', 'message': 'No se recibió texto.'}, status=400)

            ai_engine = AIEngine()
            analysis_data = ai_engine.analyze_gds_terminal(terminal_text, gds_type)
            
            # analysis_data ahora contiene {'boletos': [...]}
            return render(request, 'core/intelligence/partials/analysis_results.html', {
                'data': analysis_data
            })
        except Exception as e:
            logger.error(f"Error procesando GDS Analysis AJAX: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class GDSInjectERPView(LoginRequiredMixin, View):
    """
    Recibe el análisis del GDS Analyzer y lo convierte en una Venta real
    dentro del ERP, soportando MÚLTIPLES PASAJEROS.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            # 'analysis_data' ahora es el objeto ResultadoParseoSchema -> {'boletos': [...]}
            root_data = data.get('analysis_data', {})
            boletos_list = root_data.get('boletos', [])
            
            if not boletos_list:
                # Fallback por si la IA devolvió un solo objeto directamente (backward compatibility interna)
                if 'itinerario' in root_data:
                    boletos_list = [root_data]
                else:
                    return JsonResponse({'status': 'error', 'message': 'No se encontraron boletos en el análisis.'}, status=400)

            user_fees = data.get('user_fees', {})
            
            agencia = getattr(request.user, 'agencia', None)
            if not agencia and hasattr(request.user, 'agencias'):
                ua = request.user.agencias.filter(activo=True).first()
                agencia = ua.agencia if ua else None

            if not agencia:
                return JsonResponse({'status': 'error', 'message': 'Agencia no encontrada.'}, status=400)

            with transaction.atomic():
                # 1. Resolver Cliente Pagador
                pagador_id = data.get('pagador_id')
                cliente_pagador = None
                if pagador_id:
                    cliente_pagador = Cliente.objects.filter(id_cliente=pagador_id, agencia=agencia).first()
                
                # Si no hay pagador manual, usamos el primer pasajero del análisis para buscar/crear
                if not cliente_pagador:
                    primer_b = boletos_list[0]
                    cliente_pagador = self._resolver_cliente(primer_b, agencia)

                # 2. Aplicar Fees y Sanitización a cada boleto en la lista
                fee_prov_total = Decimal(str(user_fees.get('fee_proveedor', 0)))
                fee_int_total = Decimal(str(user_fees.get('fee_interno', 0)))
                
                # Prorrateamos los fees entre el número de boletos
                num_boletos = len(boletos_list)
                fee_prov_pax = fee_prov_total / num_boletos
                fee_int_pax = fee_int_total / num_boletos

                for b in boletos_list:
                    # Sanitización 3-CHAR y financiera
                    self._sanitizar_boleto_data(b)
                    
                    # Recalcular Total con Fees e IGTF
                    gds_total = Decimal(str(b.get('total', 0)))
                    subtotal = gds_total + fee_prov_pax + fee_int_pax
                    igtf = subtotal * Decimal('0.03')
                    b['total'] = float(round(subtotal + igtf, 2))
                    b['igtf_calculado'] = float(round(igtf, 2))

                # 3. Llamar al Builder Multipax
                venta = VentaBuilderService.construir_venta_multipax(agencia, boletos_list, cliente_pagador)

            # Redirección
            try:
                redirect_url = reverse('core:editar_venta', kwargs={'pk': venta.pk})
            except:
                redirect_url = f"/admin/core/venta/{venta.pk}/change/"
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Venta creada con {len(boletos_list)} pasajero(s).',
                'redirect_url': redirect_url
            })
            
        except Exception as e:
            logger.error(f"❌ Error inyectando GDS al ERP: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def _resolver_cliente(self, b_data, agencia):
        """Lógica de resolución de cliente (basada en la implementación anterior)."""
        doc = b_data.get('codigo_identificacion')
        nombre_completo = str(b_data.get('nombre_pasajero', 'PASAJERO/GDS')).upper().strip()
        
        nombres = ""
        apellidos = ""
        if '/' in nombre_completo:
            parts = nombre_completo.split('/')
            apellidos = parts[0].strip()
            nombres = parts[1].strip() if len(parts) > 1 else ""
        else:
            nombres = nombre_completo
            apellidos = "GDS"

        cliente = None
        if doc and str(doc).strip() not in ('None', '', 'N/A'):
            cliente = Cliente.objects.filter(cedula_identidad=str(doc)[:20], agencia=agencia).first()
        
        if not cliente:
            cliente = Cliente.objects.filter(nombres__iexact=nombres, apellidos__iexact=apellidos, agencia=agencia).first()
            
        if not cliente:
            cliente = Cliente.objects.create(
                nombres=str(nombres)[:70],
                apellidos=str(apellidos)[:70],
                cedula_identidad=str(doc)[:20] if doc else None,
                agencia=agencia,
                tipo_cliente='NAT'
            )
        return cliente

    def _sanitizar_boleto_data(self, b):
        """Aplica blindaje de 3 caracteres y normalización financiera."""
        if 'nombre_aerolinea' in b: b['nombre_aerolinea'] = str(b['nombre_aerolinea'])[:3].upper()
        if 'moneda' in b: b['moneda'] = str(b['moneda'])[:3].upper()
        
        if 'itinerario' in b and isinstance(b['itinerario'], list):
            for seg in b['itinerario']:
                if 'aerolinea' in seg: seg['aerolinea'] = str(seg['aerolinea'])[:3].upper()
                if 'origen' in seg: seg['origen'] = str(seg['origen'])[:3].upper()
                if 'destino' in seg: seg['destino'] = str(seg['destino'])[:3].upper()

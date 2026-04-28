import logging
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.crm.models import Cliente
from apps.bookings.models import Venta, BoletoImportado

logger = logging.getLogger(__name__)

class GlobalOmnisearchView(LoginRequiredMixin, View):
    """
    Endpoint ultra-rápido invocado por HTMX cuando el usuario escribe en el Ctrl+K.
    """
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()
        
        # Si la búsqueda es muy corta, no saturamos la BD
        if len(q) < 2:
            return HttpResponse('')

        errores = []
        clientes = []
        ventas = []
        boletos = []

        # 1. Buscar Clientes
        try:
            clientes = list(Cliente.objects.filter(
                Q(nombres__icontains=q) | Q(apellidos__icontains=q) | Q(email__icontains=q)
            )[:5])
        except Exception as e:
            logger.error(f"Error buscando clientes: {e}")
            errores.append(f"Clientes: {str(e)}")

        # 2. Buscar Ventas
        try:
            ventas = list(Venta.objects.filter(localizador__icontains=q)[:5])
        except Exception as e:
            logger.error(f"Error buscando ventas: {e}")
            errores.append(f"Ventas: {str(e)}")

        # 3. Buscar Boletos (Resiliencia total)
        try:
            # Intentamos búsqueda completa incluyendo nombre de pasajero
            boletos = list(BoletoImportado.objects.filter(
                Q(numero_boleto__icontains=q) | 
                Q(localizador_pnr__icontains=q) |
                Q(nombre_pasajero_completo__icontains=q)
            )[:5])
        except Exception as e:
            logger.warning(f"Fallo búsqueda extendida en boletos, reintentando básica: {e}")
            try:
                # Fallback a búsqueda básica si el campo de nombre falla (ej. property o DB issue)
                boletos = list(BoletoImportado.objects.filter(
                    Q(numero_boleto__icontains=q) | Q(localizador_pnr__icontains=q)
                )[:5])
                errores.append(f"Boletos (Búsqueda parcial): {str(e)}")
            except Exception as e2:
                logger.error(f"Error total en boletos: {e2}")
                errores.append(f"Boletos: {str(e2)}")

        context = {
            'query': q,
            'clientes': clientes,
            'ventas': ventas,
            'boletos': boletos,
            'errores': errores,
            'total_resultados': len(clientes) + len(ventas) + len(boletos)
        }
        
        return render(request, 'core/partials/omnisearch_results.html', context)


from django.http import JsonResponse

class ClienteSearchAPIView(LoginRequiredMixin, View):
    """
    API rápida para el buscador de pagadores en el GDS Analyzer.
    """
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()
        if len(q) < 3:
            return JsonResponse({'results': []})
        
        clientes = Cliente.objects.filter(
            Q(nombres__icontains=q) | 
            Q(apellidos__icontains=q) | 
            Q(cedula_identidad__icontains=q)
        ).only('id_cliente', 'nombres', 'apellidos', 'cedula_identidad')[:10]
        
        results = [
            {
                'id': c.id_cliente,
                'text': f"{c.nombres} {c.apellidos}".strip(),
                'documento': getattr(c, 'cedula_identidad', 'N/A')
            }
            for c in clientes
        ]
        
        return JsonResponse({'results': results})

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.crm.models import Cliente, Pasajero
from apps.crm.views.pasajeros_views import CRMBaseMixin

class PasajeroConvertToClienteView(CRMBaseMixin, View):
    def post(self, request, pk, *args, **kwargs):
        pasajero = get_object_or_404(Pasajero, pk=pk)
        if pasajero.clientes.exists():
            messages.warning(request, f"El pasajero {pasajero.get_nombre_completo()} ya está vinculado a un cliente.")
            return redirect('crm:pasajero_detail', pk=pk)
        
        try:
            nuevo_cliente = Cliente.objects.create(
                nombres=pasajero.nombres,
                apellidos=pasajero.apellidos,
                numero_pasaporte=pasajero.numero_pasaporte,
                cedula_identidad=pasajero.cedula_identidad,
                fecha_nacimiento=pasajero.fecha_nacimiento,
                nacionalidad=pasajero.nacionalidad,
                email=pasajero.email,
                telefono_principal=pasajero.telefono,
                foto_perfil=pasajero.foto_perfil,
                agencia=pasajero.agencia,
                tipo_cliente='IND'
            )
            nuevo_cliente.pasajeros.add(pasajero)
            messages.success(request, f"El pasajero {pasajero.get_nombre_completo()} fue convertido a Cliente exitosamente.")
            return redirect('crm:cliente_detail', pk=nuevo_cliente.pk)
        except IntegrityError:
            messages.error(request, f"Error: Ya existe un Cliente registrado con este mismo documento ({pasajero.numero_documento}).")
            return redirect('crm:pasajero_detail', pk=pk)

class PasajeroSearchView(CRMBaseMixin, View):
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()
        if len(q) < 2:
            return HttpResponse('<p class="text-gray-500 text-sm text-center py-4">Sigue escribiendo...</p>')
            
        pasajeros = Pasajero.objects.filter(
            Q(nombres__icontains=q) | 
            Q(apellidos__icontains=q) | 
            Q(numero_pasaporte__icontains=q) |
            Q(cedula_identidad__icontains=q)
        ).exclude(clientes=request.GET.get('cliente_id'))[:10]
        
        return render(request, 'crm/partials/pasajero_search_results.html', {
            'pasajeros': pasajeros,
            'cliente_id': request.GET.get('cliente_id')
        })

class VincularPasajeroActionView(CRMBaseMixin, View):
    def post(self, request, pk, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=pk)
        pasajero_id = request.POST.get('pasajero_id')
        if pasajero_id:
            pasajero = get_object_or_404(Pasajero, pk=pasajero_id)
            cliente.pasajeros.add(pasajero)
            messages.success(request, f"Pasajero {pasajero.get_nombre_completo()} vinculado.")
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

from django.views.generic import ListView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.db.models import Sum, Q, F
from django.contrib import messages
from django.utils import timezone

from core.models_catalogos import Proveedor
from core.models import LiquidacionProveedor, ItemLiquidacion, ItemVenta
from core.mixins import SaaSMixin

class LiquidacionListView(LoginRequiredMixin, ListView):
    model = LiquidacionProveedor
    template_name = 'finance/liquidaciones/dashboard.html'
    context_object_name = 'liquidaciones'
    paginate_by = 20

    def get_queryset(self):
        # Iniciamos el queryset base con relaciones optimizadas
        queryset = LiquidacionProveedor.objects.all().select_related('proveedor', 'venta').order_by('-fecha_emision')
        
        # Implementación manual de filtrado por Agencia (SaaS)
        user = self.request.user
        if not user.is_superuser:
            # Intentar obtener la agencia activa del usuario
            if hasattr(user, 'agencias'):
                usuario_agencia = user.agencias.filter(activo=True).first()
                if usuario_agencia:
                    # Filtramos por la agencia del proveedor (ya que el modelo Liquidación no tiene campo agencia directo)
                    queryset = queryset.filter(proveedor__agencia=usuario_agencia.agencia)
                else:
                    return queryset.none()
        
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(proveedor__nombre__icontains=q)
            
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Liquidaciones a Proveedores'
        context['active_tab'] = 'finance'
        context['estados_liquidacion'] = LiquidacionProveedor.EstadoLiquidacion.choices
        
        # Totales
        totales = self.get_queryset().aggregate(
            total_pendiente=Sum('saldo_pendiente'),
            total_pagado=Sum('monto_pagado')
        )
        context['total_pendiente'] = totales['total_pendiente'] or 0
        context['total_pagado'] = totales['total_pagado'] or 0
        return context

class LiquidacionCreateView(SaaSMixin, LoginRequiredMixin, TemplateView):
    template_name = 'finance/liquidaciones/wizard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Liquidación'
        context['active_tab'] = 'finance'
        context['proveedores'] = Proveedor.objects.filter(activo=True).order_by('nombre')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'load_items':
            proveedor_id = request.POST.get('proveedor')
            if not proveedor_id:
                return render(request, 'finance/liquidaciones/partials/items_list.html', {'items': []})
            
            # Buscar items de venta de este proveedor que NO tengan liquidación asociada (o su liquidación esté anulada)
            # ItemLiquidacion tiene OneToOne con ItemVenta.
            # Debemos buscar ItemVenta donde itemliquidacion es NULL.
            
            items = ItemVenta.objects.filter(
                proveedor_servicio_id=proveedor_id,
                itemliquidacion__isnull=True,
                venta__estado__in=['CON', 'COM']  # Solo ventas confirmadas o completadas
            ).select_related('venta', 'producto_servicio', 'venta__cliente', 'venta__agencia').order_by('venta__fecha_venta')
            
            return render(request, 'finance/liquidaciones/partials/items_list.html', {'items': items})
            
        elif action == 'create_liquidacion':
            proveedor_id = request.POST.get('proveedor_id')
            selected_items_ids = request.POST.getlist('selected_items')
            notas = request.POST.get('notas', '')
            
            if not proveedor_id or not selected_items_ids:
                messages.error(request, "Debe seleccionar un proveedor y al menos un item.")
                return redirect('finance:liquidacion_create')

            try:
                proveedor = Proveedor.objects.get(pk=proveedor_id)
                items_venta = ItemVenta.objects.filter(id_item_venta__in=selected_items_ids)
                
                # Calcular total
                # Usaremos el costo_unitario_referencial como base, pero idealmente deberíamos tener un 'costo_real'
                # Si no hay costo, usamos 0.
                total_monto = 0
                items_para_crear = []
                
                for item in items_venta:
                    # Lógica simplificada: Costo Referencial * Cantidad
                    costo = (item.costo_unitario_referencial or 0) * item.cantidad
                    if costo == 0:
                         # Fallback: Si no hay costo, quizás cobrar un % del precio? O alertar?
                         # Por ahora asumimos precio venta como peor caso si no hay costo (para evitar 0), pero es peligroso.
                         # Mejor: dejar en 0 y que el usuario edite?
                         # Vamos a confiar en costo_unitario.
                         pass
                    
                    total_monto += costo
                    items_para_crear.append({
                        'item_venta': item,
                        'monto': costo,
                        'descripcion': f"{item.producto_servicio.nombre} - Venta #{item.venta.localizador}"
                    })
                
                liquidacion = LiquidacionProveedor.objects.create(
                    proveedor=proveedor,
                    fecha_emision=timezone.now(),
                    monto_total=total_monto,
                    notas=notas,
                    estado=LiquidacionProveedor.EstadoLiquidacion.PENDIENTE
                )
                
                for data in items_para_crear:
                    ItemLiquidacion.objects.create(
                        liquidacion=liquidacion,
                        item_venta=data['item_venta'],
                        monto=data['monto'],
                        descripcion=data['descripcion']
                    )
                
                liquidacion.save() # Trigger saldo update logic
                
                messages.success(request, f"Liquidación #{liquidacion.id_liquidacion} creada exitosamente.")
                return redirect('finance:liquidacion_list')
                
            except Exception as e:
                messages.error(request, f"Error al crear liquidación: {str(e)}")
                return redirect('finance:liquidacion_create')
                
        return redirect('finance:liquidacion_create')

class LiquidacionDetailView(SaaSMixin, LoginRequiredMixin, DetailView):
    model = LiquidacionProveedor
    template_name = 'finance/liquidaciones/detail.html'
    context_object_name = 'liquidacion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Liquidación #{self.object.pk}'
        context['active_tab'] = 'finance'
        return context

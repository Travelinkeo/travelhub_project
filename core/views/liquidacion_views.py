# core/views/liquidacion_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from core.models import LiquidacionProveedor, ItemLiquidacion
from core.serializers import LiquidacionProveedorSerializer, ItemLiquidacionSerializer
from core.throttling import LiquidacionRateThrottle


class LiquidacionProveedorViewSet(viewsets.ModelViewSet):
    queryset = LiquidacionProveedor.objects.all().select_related('proveedor', 'venta')
    serializer_class = LiquidacionProveedorSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [LiquidacionRateThrottle]
    filterset_fields = ['estado', 'proveedor', 'venta']
    search_fields = ['id_liquidacion', 'proveedor__nombre', 'venta__localizador']
    ordering_fields = ['fecha_emision', 'monto_total', 'saldo_pendiente']
    ordering = ['-fecha_emision']

    @action(detail=True, methods=['post'])
    def marcar_pagada(self, request, pk=None):
        liquidacion = self.get_object()
        liquidacion.monto_pagado = liquidacion.monto_total
        liquidacion.estado = 'PAG'
        liquidacion.save()
        return Response({'status': 'Liquidación marcada como pagada'})

    @action(detail=True, methods=['post'])
    def registrar_pago_parcial(self, request, pk=None):
        from decimal import Decimal
        liquidacion = self.get_object()
        monto = request.data.get('monto')
        
        if not monto:
            return Response({'error': 'Monto requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        monto = Decimal(str(monto))
        if monto > liquidacion.saldo_pendiente:
            return Response({'error': 'Monto excede saldo pendiente'}, status=status.HTTP_400_BAD_REQUEST)
        
        liquidacion.monto_pagado += monto
        liquidacion.save()
        
        return Response({
            'status': 'Pago registrado',
            'saldo_pendiente': float(liquidacion.saldo_pendiente),
            'estado': liquidacion.estado
        })

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        liquidaciones = self.queryset.filter(estado='PEN')
        serializer = self.get_serializer(liquidaciones, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_proveedor(self, request):
        proveedor_id = request.query_params.get('proveedor_id')
        if not proveedor_id:
            return Response({'error': 'proveedor_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        liquidaciones = self.queryset.filter(proveedor_id=proveedor_id)
        serializer = self.get_serializer(liquidaciones, many=True)
        return Response(serializer.data)


class ItemLiquidacionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ItemLiquidacion.objects.all().select_related('liquidacion', 'item_venta')
    serializer_class = ItemLiquidacionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['liquidacion']

"""
Views para facturas consolidadas con normativa venezolana.
"""

from rest_framework import viewsets, permissions, filters
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import FacturaConsolidada, ItemFacturaConsolidada, Venta
from core.serializers_facturacion_consolidada import (
    FacturaConsolidadaSerializer,
    ItemFacturaConsolidadaSerializer
)


class FacturaConsolidadaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de facturas consolidadas con normativa venezolana.
    
    Incluye:
    - Dualidad monetaria USD/BSD
    - Cálculos automáticos de IVA, IGTF
    - Tipos de operación (Intermediación, Venta Propia, Exportación)
    - Conversión automática a bolívares
    """
    
    queryset = FacturaConsolidada.objects.select_related(
        'cliente',
        'moneda',
        'venta_asociada'
    ).prefetch_related(
        'items_factura',
        'documentos_exportacion'
    ).all()
    
    serializer_class = FacturaConsolidadaSerializer
    
    authentication_classes = [
        SessionAuthentication,
        JWTAuthentication,
        TokenAuthentication
    ]
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'numero_factura',
        'numero_control',
        'cliente__nombre',
        'cliente__rif_cedula',
        'emisor_rif'
    ]
    ordering_fields = ['fecha_emision', 'numero_factura', 'monto_total']
    ordering = ['-fecha_emision']
    
    @action(detail=True, methods=['post'])
    def recalcular(self, request, pk=None):
        """Recalcular totales de la factura"""
        factura = self.get_object()
        factura.recalcular_totales()
        serializer = self.get_serializer(factura)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        """Obtener facturas con saldo pendiente"""
        facturas = self.queryset.filter(
            saldo_pendiente__gt=0,
            estado__in=['EMI', 'PAR', 'VEN']
        )
        page = self.paginate_queryset(facturas)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(facturas, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def generar_pdf(self, request, pk=None):
        """Generar PDF de la factura"""
        from core.services.factura_pdf_generator import guardar_pdf_factura
        
        factura = self.get_object()
        success = guardar_pdf_factura(factura)
        
        if success:
            serializer = self.get_serializer(factura)
            return Response({
                'message': 'PDF generado exitosamente',
                'factura': serializer.data
            })
        else:
            return Response(
                {'error': 'Error al generar PDF'},
                status=400
            )
    
    @action(detail=True, methods=['post'])
    def contabilizar(self, request, pk=None):
        """Generar asiento contable y contabilizar la factura"""
        from core.services.factura_contabilidad import contabilizar_factura
        
        factura = self.get_object()
        
        if factura.estado == 'BOR':
            factura.estado = 'EMI'
            factura.save()
        
        success = contabilizar_factura(factura)
        
        if success:
            serializer = self.get_serializer(factura)
            return Response({
                'message': 'Factura contabilizada exitosamente',
                'factura': serializer.data
            })
        else:
            return Response(
                {'error': 'Error al contabilizar factura'},
                status=400
            )
    
    @action(detail=False, methods=['post'])
    def doble_facturacion(self, request):
        """Generar doble facturación automática (tercero + propia)"""
        from core.services.doble_facturacion import DobleFacturacionService
        from core.models import Venta
        from decimal import Decimal
        
        venta_id = request.data.get('venta_id')
        datos_tercero = request.data.get('datos_tercero')
        fee_servicio = request.data.get('fee_servicio')
        
        if not all([venta_id, datos_tercero, fee_servicio]):
            return Response(
                {'error': 'Se requieren venta_id, datos_tercero y fee_servicio'},
                status=400
            )
        
        try:
            venta = Venta.objects.get(id_venta=venta_id)
            fee_servicio = Decimal(str(fee_servicio))
            
            factura_tercero, factura_propia = DobleFacturacionService.generar_facturas_venta(
                venta, datos_tercero, fee_servicio
            )
            
            return Response({
                'message': 'Doble facturación generada exitosamente',
                'factura_tercero': self.get_serializer(factura_tercero).data,
                'factura_propia': self.get_serializer(factura_propia).data
            })
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class ItemFacturaConsolidadaViewSet(viewsets.ModelViewSet):
    """ViewSet para items de factura consolidada"""
    
    queryset = ItemFacturaConsolidada.objects.select_related('factura').all()
    serializer_class = ItemFacturaConsolidadaSerializer
    
    authentication_classes = [
        SessionAuthentication,
        JWTAuthentication,
        TokenAuthentication
    ]
    permission_classes = [permissions.IsAuthenticated]

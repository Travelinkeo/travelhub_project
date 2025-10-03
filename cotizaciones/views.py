from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from .models import Cotizacion, ItemCotizacion
from .serializers import CotizacionSerializer, ItemCotizacionSerializer


class CotizacionViewSet(viewsets.ModelViewSet):
    queryset = Cotizacion.objects.select_related('cliente', 'consultor').prefetch_related('items').order_by('-fecha_emision')
    serializer_class = CotizacionSerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['post'])
    def convertir_a_venta(self, request, pk=None):
        """Convierte la cotización en una venta"""
        cotizacion = self.get_object()
        
        try:
            venta = cotizacion.convertir_a_venta()
            return Response({
                'message': 'Cotización convertida exitosamente',
                'venta_id': venta.id_venta,
                'localizador': venta.localizador
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def marcar_enviada(self, request, pk=None):
        """Marca la cotización como enviada"""
        cotizacion = self.get_object()
        cotizacion.estado = Cotizacion.EstadoCotizacion.ENVIADA
        cotizacion.fecha_envio = timezone.now()
        cotizacion.email_enviado = True
        cotizacion.save(update_fields=['estado', 'fecha_envio', 'email_enviado'])
        
        return Response({'message': 'Cotización marcada como enviada'})
    
    @action(detail=True, methods=['post'])
    def marcar_vista(self, request, pk=None):
        """Marca la cotización como vista por el cliente"""
        cotizacion = self.get_object()
        if cotizacion.estado == Cotizacion.EstadoCotizacion.ENVIADA:
            cotizacion.estado = Cotizacion.EstadoCotizacion.VISTA
            cotizacion.fecha_vista = timezone.now()
            cotizacion.save(update_fields=['estado', 'fecha_vista'])
        
        return Response({'message': 'Cotización marcada como vista'})


class ItemCotizacionViewSet(viewsets.ModelViewSet):
    queryset = ItemCotizacion.objects.select_related('cotizacion').all()
    serializer_class = ItemCotizacionSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        item = serializer.save()
        item.cotizacion.calcular_total()
    
    def perform_update(self, serializer):
        item = serializer.save()
        item.cotizacion.calcular_total()
    
    def perform_destroy(self, instance):
        cotizacion = instance.cotizacion
        instance.delete()
        cotizacion.calcular_total()
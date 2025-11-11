"""
ViewSets para las mejoras de boletería
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from core.models.historial_boletos import HistorialCambioBoleto
from core.models.anulaciones import AnulacionBoleto
from core.serializers_boletos import HistorialCambioBoletoSerializer, AnulacionBoletoSerializer


class HistorialCambioBoletoViewSet(viewsets.ModelViewSet):
    """ViewSet para historial de cambios de boletos"""
    queryset = HistorialCambioBoleto.objects.select_related('boleto', 'usuario').all()
    serializer_class = HistorialCambioBoletoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['boleto', 'tipo_cambio', 'usuario']
    search_fields = ['descripcion', 'boleto__numero_boleto']
    ordering = ['-fecha_cambio']


class AnulacionBoletoViewSet(viewsets.ModelViewSet):
    """ViewSet para anulaciones y reembolsos"""
    queryset = AnulacionBoleto.objects.select_related(
        'boleto', 'solicitado_por', 'aprobado_por'
    ).all()
    serializer_class = AnulacionBoletoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['boleto', 'tipo_anulacion', 'estado', 'solicitado_por']
    search_fields = ['motivo', 'boleto__numero_boleto']
    ordering = ['-fecha_solicitud']
    
    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprobar una anulación"""
        from django.utils import timezone
        
        anulacion = self.get_object()
        if anulacion.estado != 'SOL':
            return Response({'error': 'Solo se pueden aprobar anulaciones solicitadas'}, status=400)
        
        anulacion.estado = 'APR'
        anulacion.aprobado_por = request.user
        anulacion.fecha_aprobacion = timezone.now()
        anulacion.save()
        
        serializer = self.get_serializer(anulacion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """Rechazar una anulación"""
        anulacion = self.get_object()
        if anulacion.estado != 'SOL':
            return Response({'error': 'Solo se pueden rechazar anulaciones solicitadas'}, status=400)
        
        anulacion.estado = 'REC'
        anulacion.aprobado_por = request.user
        anulacion.notas = request.data.get('motivo_rechazo', '')
        anulacion.save()
        
        serializer = self.get_serializer(anulacion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def marcar_reembolsada(self, request, pk=None):
        """Marcar como reembolsada"""
        from django.utils import timezone
        
        anulacion = self.get_object()
        if anulacion.estado != 'APR':
            return Response({'error': 'Solo se pueden reembolsar anulaciones aprobadas'}, status=400)
        
        anulacion.estado = 'REE'
        anulacion.fecha_reembolso = timezone.now()
        anulacion.save()
        
        serializer = self.get_serializer(anulacion)
        return Response(serializer.data)

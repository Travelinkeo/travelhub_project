# core/views/libro_ventas_views.py
"""
Views para Libro de Ventas
"""
from datetime import datetime
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from core.services.libro_ventas import LibroVentasService


class LibroVentasViewSet(viewsets.ViewSet):
    """ViewSet para generar Libro de Ventas"""
    
    authentication_classes = [
        SessionAuthentication,
        JWTAuthentication,
        TokenAuthentication
    ]
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def generar(self, request):
        """
        Genera el libro de ventas para un período
        
        Query params:
            - fecha_inicio: YYYY-MM-DD
            - fecha_fin: YYYY-MM-DD
            - formato: json|csv (default: json)
        """
        fecha_inicio_str = request.query_params.get('fecha_inicio')
        fecha_fin_str = request.query_params.get('fecha_fin')
        formato = request.query_params.get('formato', 'json')
        
        if not fecha_inicio_str or not fecha_fin_str:
            return Response({
                'error': 'Se requieren fecha_inicio y fecha_fin (formato: YYYY-MM-DD)'
            }, status=400)
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }, status=400)
        
        # Generar libro de ventas
        libro_ventas = LibroVentasService.generar_libro_ventas(
            fecha_inicio, fecha_fin
        )
        
        if formato == 'csv':
            # Exportar a CSV
            csv_content = LibroVentasService.exportar_csv(libro_ventas)
            
            response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
            filename = f"libro_ventas_{fecha_inicio_str}_{fecha_fin_str}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        # Retornar JSON
        return Response(libro_ventas)
    
    @action(detail=False, methods=['get'])
    def resumen_mensual(self, request):
        """
        Resumen mensual del libro de ventas
        
        Query params:
            - mes: MM (1-12)
            - anio: YYYY
        """
        mes = request.query_params.get('mes')
        anio = request.query_params.get('anio')
        
        if not mes or not anio:
            return Response({
                'error': 'Se requieren mes (1-12) y anio (YYYY)'
            }, status=400)
        
        try:
            mes = int(mes)
            anio = int(anio)
            
            # Calcular primer y último día del mes
            from calendar import monthrange
            fecha_inicio = datetime(anio, mes, 1).date()
            ultimo_dia = monthrange(anio, mes)[1]
            fecha_fin = datetime(anio, mes, ultimo_dia).date()
            
        except (ValueError, TypeError):
            return Response({
                'error': 'Mes o año inválido'
            }, status=400)
        
        # Generar libro de ventas
        libro_ventas = LibroVentasService.generar_libro_ventas(
            fecha_inicio, fecha_fin
        )
        
        # Retornar solo resumen
        return Response({
            'periodo': {
                'mes': mes,
                'anio': anio,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            },
            'resumen': libro_ventas['resumen'],
            'totales': libro_ventas['totales'],
        })

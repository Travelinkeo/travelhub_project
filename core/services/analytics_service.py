
import datetime
from django.db.models import Sum, Count, F, Avg
from django.db.models.functions import TruncMonth, ExtractYear
from django.utils import timezone
from django.db import models
from apps.bookings.models import Venta
from apps.bookings.models import BoletoImportado
from django.contrib.auth import get_user_model

User = get_user_model()

class AnalyticsService:
    @staticmethod
    def get_ventas_mensuales(year=None):
        if not year:
            year = timezone.now().year
        
        # Filtrar ventas válidas (Pagadas o Completadas)
        qs = Venta.objects.filter(
            fecha_venta__year=year,
            estado__in=[Venta.EstadoVenta.PAGADA_TOTAL, Venta.EstadoVenta.COMPLETADA, Venta.EstadoVenta.CONFIRMADA]
        )

        # Agrupar por mes
        data = qs.annotate(month=TruncMonth('fecha_venta')).values('month').annotate(total=Sum('total_venta')).order_by('month')
        
        # Formatear para Chart.js [Jan, Feb...]
        labels = []
        values = []
        for entry in data:
            labels.append(entry['month'].strftime('%B'))
            values.append(float(entry['total'] or 0))
            
        return {
            'labels': labels,
            'values': values,
            'year': year
        }

    @staticmethod
    def get_top_vendedores(year=None, limit=5):
        if not year:
            year = timezone.now().year
            
        qs = Venta.objects.filter(
            fecha_venta__year=year,
             estado__in=[Venta.EstadoVenta.PAGADA_TOTAL, Venta.EstadoVenta.COMPLETADA, Venta.EstadoVenta.CONFIRMADA]
        )
        
        data = qs.values('creado_por__username').annotate(total=Sum('total_venta')).order_by('-total')[:limit]
        
        return list(data)

    @staticmethod
    def get_top_aerolineas(year=None, limit=5):
        if not year:
            year = timezone.now().year
            
        # Usamos BoletoImportado para obtener la aerolínea real
        # Filtramos boletos asociados a ventas válidas
        qs = BoletoImportado.objects.filter(
            fecha_emision_boleto__year=year
        ).exclude(aerolinea_emisora__isnull=True).exclude(aerolinea_emisora='')
        
        # Agrupar por nombre de aerolínea
        # OJO: Los nombres pueden venir sucios ("Avianca", "AVIANCA S.A."), idealmente normalizar antes, 
        # pero por ahora agrupamos raw.
        data = qs.values('aerolinea_emisora').annotate(
            count=Count('id_boleto_importado'),
            total_sales=Sum('total_boleto')
        ).order_by('-total_sales')[:limit]
        
        # Convertir Decimal a float para JSON
        result = []
        for item in data:
            result.append({
                'aerolinea': item['aerolinea_emisora'],
                'count': item['count'],
                'total': float(item['total_sales'] or 0)
            })
            
        return result

    @staticmethod
    def get_kpis_resumen(year=None):
        if not year:
            year = timezone.now().year
            
        qs = Venta.objects.filter(fecha_venta__year=year)
        
        return {
            'total_ventas': qs.aggregate(Sum('total_venta'))['total_venta__sum'] or 0,
            'total_transacciones': qs.count(),
            'ticket_promedio': qs.aggregate(avg=Avg('total_venta'))['avg'] or 0
        }

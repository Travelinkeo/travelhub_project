"""Analytics y métricas de SaaS."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from core.models.agencia import Agencia


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_mrr(request):
    """Calcula el MRR (Monthly Recurring Revenue)."""
    plan_prices = {
        'BASIC': 29,
        'PRO': 99,
        'ENTERPRISE': 299,
    }
    
    agencias_activas = Agencia.objects.filter(
        activa=True
    ).exclude(plan='FREE').values('plan').annotate(count=Count('id'))
    
    mrr_total = 0
    mrr_por_plan = {}
    
    for item in agencias_activas:
        plan = item['plan']
        count = item['count']
        price = plan_prices.get(plan, 0)
        mrr = price * count
        mrr_total += mrr
        mrr_por_plan[plan] = {
            'agencias': count,
            'precio': price,
            'mrr': mrr
        }
    
    return Response({
        'mrr_total': mrr_total,
        'mrr_por_plan': mrr_por_plan,
        'arr': mrr_total * 12,  # Annual Recurring Revenue
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_churn_rate(request):
    """Calcula el churn rate (tasa de cancelación)."""
    hace_30_dias = timezone.now() - timedelta(days=30)
    
    # Agencias que cancelaron en los últimos 30 días
    canceladas = Agencia.objects.filter(
        activa=False,
        fecha_actualizacion__gte=hace_30_dias
    ).count()
    
    # Total de agencias activas hace 30 días
    total_hace_30_dias = Agencia.objects.filter(
        fecha_creacion__lt=hace_30_dias
    ).count()
    
    churn_rate = (canceladas / total_hace_30_dias * 100) if total_hace_30_dias > 0 else 0
    
    return Response({
        'canceladas_30_dias': canceladas,
        'total_hace_30_dias': total_hace_30_dias,
        'churn_rate': round(churn_rate, 2),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_usage_metrics(request):
    """Obtiene métricas de uso por plan."""
    agencias = Agencia.objects.filter(activa=True)
    
    metrics_por_plan = {}
    
    for plan in ['FREE', 'BASIC', 'PRO', 'ENTERPRISE']:
        agencias_plan = agencias.filter(plan=plan)
        
        if agencias_plan.exists():
            metrics_por_plan[plan] = {
                'total_agencias': agencias_plan.count(),
                'promedio_ventas': agencias_plan.aggregate(Avg('ventas_mes_actual'))['ventas_mes_actual__avg'] or 0,
                'promedio_usuarios': agencias_plan.annotate(
                    num_usuarios=Count('usuarios', filter=Q(usuarios__activo=True))
                ).aggregate(Avg('num_usuarios'))['num_usuarios__avg'] or 0,
                'uso_ventas_porcentaje': round(
                    (agencias_plan.aggregate(Avg('ventas_mes_actual'))['ventas_mes_actual__avg'] or 0) /
                    (agencias_plan.first().limite_ventas_mes or 1) * 100, 1
                ) if agencias_plan.first() else 0,
            }
    
    return Response({'metrics_por_plan': metrics_por_plan})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_conversion_funnel(request):
    """Obtiene el funnel de conversión de FREE a planes pagos."""
    total_agencias = Agencia.objects.count()
    agencias_free = Agencia.objects.filter(plan='FREE').count()
    agencias_trial_activo = Agencia.objects.filter(
        plan='FREE',
        fecha_fin_trial__gte=timezone.now().date()
    ).count()
    agencias_trial_expirado = Agencia.objects.filter(
        plan='FREE',
        fecha_fin_trial__lt=timezone.now().date()
    ).count()
    agencias_pagando = Agencia.objects.exclude(plan='FREE').count()
    
    conversion_rate = (agencias_pagando / total_agencias * 100) if total_agencias > 0 else 0
    
    return Response({
        'total_agencias': total_agencias,
        'free': {
            'total': agencias_free,
            'trial_activo': agencias_trial_activo,
            'trial_expirado': agencias_trial_expirado,
        },
        'pagando': agencias_pagando,
        'conversion_rate': round(conversion_rate, 2),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_growth_metrics(request):
    """Obtiene métricas de crecimiento."""
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    hace_30_dias = hoy - timedelta(days=30)
    
    nuevas_7_dias = Agencia.objects.filter(fecha_creacion__gte=hace_7_dias).count()
    nuevas_30_dias = Agencia.objects.filter(fecha_creacion__gte=hace_30_dias).count()
    
    return Response({
        'nuevas_agencias': {
            'ultimos_7_dias': nuevas_7_dias,
            'ultimos_30_dias': nuevas_30_dias,
            'promedio_diario_7d': round(nuevas_7_dias / 7, 1),
            'promedio_diario_30d': round(nuevas_30_dias / 30, 1),
        }
    })

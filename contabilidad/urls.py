# contabilidad/urls.py
from django.urls import path
from . import views
from .views_tasas import (
    obtener_tasas_actuales,
    obtener_tasa_bcv_simple,
    sincronizar_tasas_manual
)

app_name = 'contabilidad'

urlpatterns = [
    # Reportes
    path('reportes/balance-comprobacion/', views.reporte_balance_comprobacion, name='balance_comprobacion'),
    path('reportes/estado-resultados/', views.reporte_estado_resultados, name='estado_resultados'),
    path('reportes/balance-general/', views.reporte_balance_general, name='balance_general'),
    path('reportes/libro-diario/', views.reporte_libro_diario, name='libro_diario'),
    path('reportes/libro-mayor/', views.reporte_libro_mayor, name='libro_mayor'),
    
    # API Tasas de Cambio
    path('api/tasas/actuales/', obtener_tasas_actuales, name='tasas_actuales'),
    path('api/tasas/bcv/', obtener_tasa_bcv_simple, name='tasa_bcv'),
    path('api/tasas/sincronizar/', sincronizar_tasas_manual, name='sincronizar_tasas'),
]

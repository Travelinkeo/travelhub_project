# contabilidad/urls.py
from django.urls import path
from . import views

app_name = 'contabilidad'

urlpatterns = [
    path('reportes/balance-comprobacion/', views.reporte_balance_comprobacion, name='balance_comprobacion'),
    path('reportes/estado-resultados/', views.reporte_estado_resultados, name='estado_resultados'),
    path('reportes/balance-general/', views.reporte_balance_general, name='balance_general'),
    path('reportes/libro-diario/', views.reporte_libro_diario, name='libro_diario'),
    path('reportes/libro-mayor/', views.reporte_libro_mayor, name='libro_mayor'),
]

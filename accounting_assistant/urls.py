
from django.urls import path

from .views import SugerirAsientoView

app_name = 'accounting_assistant'

urlpatterns = [
    # path('', AssistantView.as_view(), name='index'),
    path('api/contabilidad/sugerir-asiento/', SugerirAsientoView.as_view(), name='sugerir_asiento'),
]

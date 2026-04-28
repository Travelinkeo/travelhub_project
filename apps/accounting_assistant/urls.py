
from django.urls import path

from .views import SugerirAsientoView, AssistantChatView

app_name = 'accounting_assistant'

urlpatterns = [
    path('api/contabilidad/chat/', AssistantChatView.as_view(), name='chat'),
    path('api/contabilidad/sugerir-asiento/', SugerirAsientoView.as_view(), name='sugerir_asiento'),
]

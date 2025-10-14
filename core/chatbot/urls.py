# core/chatbot/urls.py

from django.urls import path
from .views import chat_message, get_quick_replies, chatbot_status

app_name = 'chatbot'

urlpatterns = [
    path('message/', chat_message, name='chat_message'),
    path('quick-replies/', get_quick_replies, name='quick_replies'),
    path('status/', chatbot_status, name='status'),
]
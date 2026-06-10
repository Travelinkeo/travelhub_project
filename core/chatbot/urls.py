# core/chatbot/urls.py

from django.urls import path

from .views import chat_message, chatbot_status, get_quick_replies

app_name = "chatbot"

urlpatterns = [
    path("message/", chat_message, name="chat_message"),
    path("quick-replies/", get_quick_replies, name="quick_replies"),
    path("status/", chatbot_status, name="status"),
]

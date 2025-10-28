"""Views de autenticación y health check"""
import os
from django.contrib.auth import authenticate
from django.db import connection
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_ok = False
        payload = {
            'status': 'ok' if db_ok else 'degraded',
            'db': db_ok,
            'time': timezone.now().isoformat(),
            'version': os.getenv('APP_VERSION', 'dev')
        }
        return Response(payload, status=200 if db_ok else 503)


class LoginView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'detail': 'username y password requeridos'}, status=400)
        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({'detail': 'Credenciales inválidas'}, status=401)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})

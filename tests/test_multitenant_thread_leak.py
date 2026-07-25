"""Tests para Multitenant thread leak."""
import threading
import time

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore

from core.middleware import (
    ThreadLocalContextMiddleware,
    get_current_agency,
    get_current_user,
)
from core.models.agencia import Agencia, UsuarioAgencia

User = get_user_model()


class MockRequest:
    """Mock Request."""
    def __init__(self, user, agency, session):
        self.user = user
        self.agencia = agency
        self.agency = agency
        self.session = session
        self.META = {
            "HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "REMOTE_ADDR": "127.0.0.1",
        }
        self.path = "/api/test/"


@pytest.mark.django_db(transaction=True)
def test_multitenant_thread_concurrency_leak():
    """
    Simula peticiones concurrentes en múltiples hilos reutilizados.
    Verifica que no hay fugas ni contaminación cruzada de agencias/usuarios entre hilos.
    """
    # 1. Crear agencias de prueba
    agencia_a = Agencia.objects.create(nombre="Agencia A", activa=True)
    agencia_b = Agencia.objects.create(nombre="Agencia B", activa=True)

    # 2. Crear usuarios de prueba
    user_a = User.objects.create_user(username="usera", email="usera@test.com", password="password")
    user_b = User.objects.create_user(username="userb", email="userb@test.com", password="password")

    # 3. Vincular los usuarios a las agencias correspondientes
    UsuarioAgencia.objects.create(usuario=user_a, agencia=agencia_a, rol="vendedor", activo=True)
    UsuarioAgencia.objects.create(usuario=user_b, agencia=agencia_b, rol="vendedor", activo=True)

    errors = []

    def get_response_a(request):
        # Simula procesamiento de la petición.
        """Get response a."""
        time.sleep(0.02)
        current_agency = get_current_agency()
        current_user = get_current_user()
        if current_agency != agencia_a:
            errors.append(f"Fuga detectada! Esperaba Agencia A, obtuve {current_agency}")
        if current_user != user_a:
            errors.append(f"Fuga detectada! Esperaba User A, obtuve {current_user}")
        from django.http import HttpResponse

        return HttpResponse("OK")

    def get_response_b(request):
        """Get response b."""
        time.sleep(0.02)
        current_agency = get_current_agency()
        current_user = get_current_user()
        if current_agency != agencia_b:
            errors.append(f"Fuga detectada! Esperaba Agencia B, obtuve {current_agency}")
        if current_user != user_b:
            errors.append(f"Fuga detectada! Esperaba User B, obtuve {current_user}")
        from django.http import HttpResponse

        return HttpResponse("OK")

    def run_client_a():
        """Run client a."""
        middleware = ThreadLocalContextMiddleware(get_response=get_response_a)
        try:
            for _ in range(20):
                session = SessionStore()
                request = MockRequest(user_a, agencia_a, session)
                middleware(request)
                # Después de la ejecución, el hilo actual debe estar limpio
                if get_current_agency() is not None:
                    errors.append("Limpieza fallida! Quedó agencia residual en el hilo")
        finally:
            # Asegura cerrar las conexiones a la BD de este hilo al finalizar
            from django.db import connections

            connections.close_all()

    def run_client_b():
        """Run client b."""
        middleware = ThreadLocalContextMiddleware(get_response=get_response_b)
        try:
            for _ in range(20):
                session = SessionStore()
                request = MockRequest(user_b, agencia_b, session)
                middleware(request)
                if get_current_agency() is not None:
                    errors.append("Limpieza fallida! Quedó agencia residual en el hilo")
        finally:
            from django.db import connections

            connections.close_all()

    threads = []
    # Lanzamos 10 hilos concurrentes para la Agencia A y 10 para la Agencia B
    for _ in range(10):
        t1 = threading.Thread(target=run_client_a)
        t2 = threading.Thread(target=run_client_b)
        threads.extend([t1, t2])
        t1.start()
        t2.start()

    for t in threads:
        t.join()

    assert not errors, f"Se detectaron fugas de contexto: {errors}"

"""
tests/load/locustfile.py — Tests de Carga con Locust.

Simula carga realista de usuarios (agentes de viajes) sobre TravelHub.

Uso:
    # Instalar: pip install locust
    # Modo web (interactivo):
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Modo headless (CI/CD):
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           --users=50 --spawn-rate=5 --run-time=60s --headless

Escenarios cubiertos:
    - TravelHubAgent: Agente de viajes típico (dashboard, ventas, boletos)
    - AdminUser: Superusuario consultando reportes (mayor carga por request)
"""

import json
import random

from locust import HttpUser, between, events, task


class TravelHubAgent(HttpUser):
    """
    Simula un agente de viajes usando el sistema durante su jornada laboral.
    Peso: 80% del tráfico (usuario principal del sistema).
    """

    weight = 8
    wait_time = between(1, 5)  # Pausa realista entre acciones

    def on_start(self):
        """Login al inicio de la sesión."""
        response = self.client.post(
            "/api/auth/jwt/obtain/",
            json={"username": "agent@loadtest.com", "password": "loadtest123!"},
            catch_response=True,
            name="POST /api/auth/jwt/obtain/ [LOGIN]",
        )
        if response.status_code == 200:
            token = response.json().get("access")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
            response.success()
        else:
            response.failure(f"Login fallido: {response.status_code}")

    @task(5)
    def dashboard_stats(self):
        """Consulta de KPIs del dashboard (tarea más frecuente)."""
        self.client.get(
            "/api/dashboard/stats/",
            name="GET /api/dashboard/stats",
        )

    @task(4)
    def listar_ventas(self):
        """Listado de ventas paginado."""
        page = random.randint(1, 3)
        self.client.get(
            f"/api/ventas/?page={page}",
            name="GET /api/ventas",
        )

    @task(3)
    def listar_boletos(self):
        """Listado de boletos importados."""
        self.client.get(
            "/api/boletos/?page=1",
            name="GET /api/boletos",
        )

    @task(2)
    def tasa_bcv(self):
        """Consulta de tasa BCV (cached en Redis)."""
        self.client.get(
            "/api/tasas/bcv/",
            name="GET /api/tasas/bcv",
        )

    @task(2)
    def listar_clientes(self):
        """Listado de clientes del CRM."""
        self.client.get(
            "/api/clientes/?page=1",
            name="GET /api/clientes",
        )

    @task(1)
    def health_check(self):
        """Health check del sistema."""
        with self.client.get(
            "/health/",
            name="GET /health",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check fallido: {resp.status_code}")


class AdminReports(HttpUser):
    """
    Simula un administrador consultando reportes pesados.
    Peso: 20% del tráfico, requests más costosos.
    """

    weight = 2
    wait_time = between(5, 15)  # Admins hacen menos requests pero más pesados

    def on_start(self):
        response = self.client.post(
            "/api/auth/jwt/obtain/",
            json={"username": "admin@loadtest.com", "password": "loadtest123!"},
            catch_response=True,
            name="POST /api/auth/jwt/obtain/ [ADMIN LOGIN]",
        )
        if response.status_code == 200:
            token = response.json().get("access")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
            response.success()
        else:
            response.failure(f"Admin login fallido: {response.status_code}")

    @task(3)
    def reporte_ventas(self):
        """Reporte de ventas del mes (query pesada)."""
        self.client.get(
            "/api/ventas/?page=1&page_size=100",
            name="GET /api/ventas [reporte]",
        )

    @task(2)
    def audit_logs(self):
        """Consulta de logs de auditoría."""
        self.client.get(
            "/api/audit-logs/?page=1",
            name="GET /api/audit-logs",
        )

    @task(1)
    def dashboard_stats(self):
        """KPIs del dashboard desde perspectiva admin."""
        self.client.get(
            "/api/dashboard/stats/",
            name="GET /api/dashboard/stats [admin]",
        )


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Reporte final al terminar la prueba."""
    stats = environment.runner.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    avg_response_time = stats.total.avg_response_time

    print(f"\n{'='*50}")
    print("📊 RESUMEN DE PRUEBA DE CARGA — TravelHub")
    print(f"{'='*50}")
    print(f"Total requests: {total_requests}")
    print(f"Fallos: {total_failures} ({(total_failures/max(total_requests,1)*100):.1f}%)")
    print(f"Tiempo de respuesta promedio: {avg_response_time:.0f}ms")
    print(f"{'='*50}")

    # Fallar si hay más del 1% de errores
    if total_failures / max(total_requests, 1) > 0.01:
        environment.process_exit_code = 1
        print("❌ PRUEBA FALLIDA: Tasa de error > 1%")
    else:
        print("✅ PRUEBA APROBADA: Tasa de error < 1%")

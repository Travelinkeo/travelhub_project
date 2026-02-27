from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Simula un usuario navegando por las rutas críticas'

    def handle(self, *args, **kwargs):
        client = Client()
        User = get_user_model()
        
        # 1. Obtener un usuario (o crear uno temporal)
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ No hay usuarios en la BD. Crea uno primero."))
            return

        client.force_login(user)
        self.stdout.write(f"🔍 Probando rutas como usuario: {user.username}")

        # 2. Lista de Rutas Críticas a probar
        rutas = [
            'core:modern_dashboard',    # Dashboard Principal (Adjusted from core:dashboard)
            'core:upload_boleto',       # Endpoint de Subida (POST)
            # 'core:editar_venta',      # (Requiere ID, la probaremos manualmente)
        ]

        for ruta_name in rutas:
            try:
                # Nota: Para upload_boleto es GET, aunque la vista espera POST, 
                # al menos verificamos que la URL resuelve y la vista existe.
                url = reverse(ruta_name)
                response = client.get(url) 
                
                if response.status_code in [200, 302, 405]: # 405 es ok para vistas solo POST
                    self.stdout.write(self.style.SUCCESS(f"✅ {ruta_name} ({url}) - OK (Status: {response.status_code})"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ {ruta_name} - FALLÓ (Status: {response.status_code})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {ruta_name} - ERROR CRÍTICO: {e}"))

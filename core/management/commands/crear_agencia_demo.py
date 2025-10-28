"""
Management command para crear la agencia DEMO de TravelHub.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models.agencia import Agencia, UsuarioAgencia
from personas.models import Cliente
from datetime import date, timedelta
import os


class Command(BaseCommand):
    help = 'Crea la agencia DEMO de TravelHub con datos de ejemplo'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creando agencia DEMO de TravelHub...'))
        
        # 1. Crear usuario demo
        demo_user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@travelhub.com',
                'first_name': 'Usuario',
                'last_name': 'Demo',
                'is_staff': False,
                'is_active': True,
            }
        )
        if created:
            demo_user.set_password('demo2025')
            demo_user.save()
            self.stdout.write(self.style.SUCCESS('Usuario demo creado: demo / demo2025'))
        else:
            self.stdout.write(self.style.WARNING('Usuario demo ya existe'))
        
        # 2. Crear agencia DEMO
        agencia, created = Agencia.objects.get_or_create(
            nombre='TravelHub Demo',
            defaults={
                'nombre_comercial': 'TravelHub - Agencia de Viajes',
                'rif': 'J-00000000-0',
                'iata': 'DEMO001',
                'telefono_principal': '+58 212 555-0100',
                'email_principal': 'info@travelhub.com',
                'email_ventas': 'ventas@travelhub.com',
                'direccion': 'Av. Principal, Centro Empresarial, Piso 5, Oficina 501',
                'ciudad': 'Caracas',
                'estado': 'Distrito Capital',
                'pais': 'Venezuela',
                'color_primario': '#1976d2',
                'color_secundario': '#dc004e',
                'website': 'https://travelhub.com',
                'whatsapp': '+58 414 555-0100',
                'moneda_principal': 'USD',
                'zona_horaria': 'America/Caracas',
                'idioma': 'es',
                'propietario': demo_user,
                'plan': 'PRO',  # Plan PRO para demo
                'fecha_fin_trial': date.today() + timedelta(days=365),  # 1 año
                'limite_usuarios': 10,
                'limite_ventas_mes': 1000,
                'es_demo': True,
                'activa': True,
            }
        )
        
        if created:
            # Actualizar límites por plan
            agencia.actualizar_limites_por_plan()
            self.stdout.write(self.style.SUCCESS(f'Agencia DEMO creada: {agencia.nombre}'))
        else:
            # Actualizar campos importantes
            agencia.es_demo = True
            agencia.plan = 'PRO'
            agencia.activa = True
            agencia.save()
            self.stdout.write(self.style.WARNING('Agencia DEMO ya existe, actualizada'))
        
        # 3. Asignar usuario a agencia
        usuario_agencia, created = UsuarioAgencia.objects.get_or_create(
            usuario=demo_user,
            agencia=agencia,
            defaults={
                'rol': 'admin',
                'activo': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Usuario asignado a agencia como admin'))
        
        # 4. Crear clientes de ejemplo
        clientes_creados = 0
        try:
            Cliente.objects.get_or_create(
                email='maria.gonzalez@example.com',
                defaults={'nombres': 'María', 'apellidos': 'González'}
            )
            clientes_creados += 1
        except Exception:
            pass
        
        try:
            Cliente.objects.get_or_create(
                email='carlos.rodriguez@example.com',
                defaults={'nombres': 'Carlos', 'apellidos': 'Rodríguez'}
            )
            clientes_creados += 1
        except Exception:
            pass
        
        self.stdout.write(self.style.SUCCESS(f'{clientes_creados} clientes de ejemplo creados'))
        
        # 5. Resumen
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('AGENCIA DEMO CREADA EXITOSAMENTE'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'Agencia: {agencia.nombre}')
        self.stdout.write(f'Plan: {agencia.get_plan_display()}')
        self.stdout.write(f'Usuario: demo')
        self.stdout.write(f'Password: demo2025')
        self.stdout.write(f'Email: demo@travelhub.com')
        self.stdout.write(f'Es Demo: Sí')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.WARNING('\nIMPORTANTE: Esta agencia es solo para demostraciones.'))
        self.stdout.write(self.style.WARNING('Los datos no son reales y pueden ser reseteados en cualquier momento.\n'))

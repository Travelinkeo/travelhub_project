"""
Management command para crear usuarios asesores y agencia de pruebas.

Uso:
    python manage.py crear_usuarios_demo
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models.agencia import Agencia, UsuarioAgencia


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Crea usuarios asesores para Travelinkeo y la agencia de pruebas TravelHub Demo"

    def handle(self, *args, **options):
        """Método: handle."""
        sep = "=" * 60
        self.stdout.write(sep)
        self.stdout.write("  CREANDO USUARIOS PARA TRAVELINKEO")
        self.stdout.write(sep)

        # Buscar agencia Travelinkeo
        try:
            agencia_travelinkeo = Agencia.objects.get(nombre="Travelinkeo")
            self.stdout.write(f"  [OK] Agencia encontrada: {agencia_travelinkeo.nombre}")
        except Agencia.DoesNotExist:
            self.stderr.write(
                "  [ERROR] No se encontro la agencia 'Travelinkeo'. Agencias existentes:"
            )
            for a in Agencia.objects.all():
                self.stderr.write(f"     - '{a.nombre}'")
            return

        USUARIOS = [
            {"username": "NaidaCohenVentas", "first_name": "Naida", "last_name": "Cohen"},
            {"username": "ArmandoAlemanVentas", "first_name": "Armando", "last_name": "Aleman"},
        ]

        usuarios_creados = []
        for datos in USUARIOS:
            user, created = User.objects.get_or_create(username=datos["username"])
            user.first_name = datos["first_name"]
            user.last_name = datos["last_name"]
            user.set_password("viaggio1")
            user.is_active = True
            user.save()

            ua, ua_created = UsuarioAgencia.objects.get_or_create(
                usuario=user,
                agencia=agencia_travelinkeo,
                defaults={"rol": "vendedor", "activo": True},
            )
            if not ua_created:
                ua.rol = "vendedor"
                ua.activo = True
                ua.save()

            estado = "CREADO" if created else "ACTUALIZADO"
            self.stdout.write(
                f"  [{estado}] {user.username} -> {agencia_travelinkeo.nombre} | rol: vendedor"
            )
            usuarios_creados.append(user)

        # Crear agencia de pruebas
        self.stdout.write("\n" + sep)
        self.stdout.write("  CREANDO AGENCIA DE PRUEBAS: TravelHub Demo")
        self.stdout.write(sep)

        propietario = agencia_travelinkeo.propietario
        if not propietario:
            propietario = User.objects.filter(is_superuser=True).first()
        if not propietario:
            propietario = User.objects.first()

        self.stdout.write(f"  Propietario asignado: {propietario.username}")

        agencia_demo, demo_created = Agencia.objects.get_or_create(
            nombre="TravelHub Demo",
            defaults={
                "nombre_comercial": "TravelHub (Pruebas)",
                "email_principal": "demo@travelhub.cc",
                "ciudad": "Caracas",
                "pais": "Venezuela",
                "activa": True,
                "propietario": propietario,
            },
        )

        if agencia_demo.configuracion:
            agencia_demo.configuracion.es_demo = True
            agencia_demo.configuracion.plan = "PRO"
            agencia_demo.configuracion.save(update_fields=["es_demo", "plan"])

        estado_demo = "CREADA" if demo_created else "YA EXISTIA"
        self.stdout.write(
            f"  [{estado_demo}] {agencia_demo.nombre} | plan: {agencia_demo.plan} | demo: True"
        )

        self.stdout.write("\n  Asociando usuarios a la agencia demo...")
        for user in usuarios_creados:
            ua_demo, ua_demo_created = UsuarioAgencia.objects.get_or_create(
                usuario=user,
                agencia=agencia_demo,
                defaults={"rol": "vendedor", "activo": True},
            )
            estado_ua = "ASOCIADO" if ua_demo_created else "YA EXISTIA"
            self.stdout.write(f"    [{estado_ua}] {user.username} -> {agencia_demo.nombre}")

        # Resumen
        self.stdout.write("\n" + sep)
        self.stdout.write("  RESUMEN FINAL")
        self.stdout.write(sep)
        self.stdout.write(f"  Agencia principal  : {agencia_travelinkeo.nombre}")
        self.stdout.write(
            f"  Agencia de pruebas : {agencia_demo.nombre}  (plan={agencia_demo.plan}, demo=True)"
        )
        self.stdout.write("")

        for user in usuarios_creados:
            agencias = UsuarioAgencia.objects.filter(usuario=user).select_related("agencia")
            self.stdout.write(f"  Usuario: {user.username}")
            for ua in agencias:
                self.stdout.write(f"       -> {ua.agencia.nombre}  [rol: {ua.rol}]")

        self.stdout.write("")
        self.stdout.write("  Contrasena de ambos usuarios: viaggio1")
        self.stdout.write(sep)
        self.stdout.write("  Todo listo.\n")

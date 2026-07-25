# core/management/commands/provision_tenant.py
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.finance.models_stubs import CanalRecaudacion, Moneda
from core.models.agencia import Agencia, AgenciaConfiguracion


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Aprovisiona de forma atómica y segura un nuevo inquilino (Agencia SaaS) con su entorno financiero inicial."

    def add_arguments(self, parser):
        """Método: add arguments."""
        parser.add_argument(
            "--nombre", type=str, required=True, help="Nombre comercial de la agencia piloto."
        )
        parser.add_argument(
            "--subdominio",
            type=str,
            required=True,
            help="Subdominio exclusivo para la resolución de Traefik (slug).",
        )
        parser.add_argument(
            "--contribuyente-especial",
            action="store_true",
            help="Activa si la agencia es Sujeto Pasivo Especial ante el SENIAT.",
        )
        parser.add_argument(
            "--tg-finanzas",
            type=str,
            required=False,
            default="",
            help="ID del Chat de Telegram para alertas financieras.",
        )
        parser.add_argument(
            "--tg-operaciones",
            type=str,
            required=False,
            default="",
            help="ID del Chat de Telegram para alertas de operaciones/CRM.",
        )
        parser.add_argument(
            "--propietario",
            type=str,
            required=False,
            default=None,
            help="Nombre de usuario del propietario de la agencia.",
        )

    def handle(self, *args, **options):
        """Método: handle."""
        nombre = options["nombre"]
        subdominio = options["subdominio"].lower().strip()
        es_especial = options["contribuyente_especial"]
        tg_finanzas = options["tg_finanzas"]
        tg_operaciones = options["tg_operaciones"]
        propietario_username = options["propietario"]

        self.stdout.write(
            self.style.WARNING(
                f"[*] Iniciando pipeline de aprovisionamiento para: {nombre} ({subdominio})..."
            )
        )

        # Verificación preventiva de subdominios duplicados
        if AgenciaConfiguracion.objects.filter(subdominio_slug=subdominio).exists():
            raise CommandError(
                f"[-] Error: El subdominio '{subdominio}' ya está asignado a otro inquilino."
            )

        # Resolución del Propietario
        if propietario_username:
            try:
                propietario = User.objects.get(username=propietario_username)
            except User.DoesNotExist:
                raise CommandError(
                    f"[-] Error: El usuario propietario '{propietario_username}' no existe en el sistema."
                ) from None
        else:
            # Buscar el primer superusuario o usuario activo disponible como fallback
            propietario = User.objects.filter(is_superuser=True).first()
            if not propietario:
                propietario = User.objects.filter(is_active=True).first()

            if not propietario:
                raise CommandError(
                    "[-] Error de Sistema: No hay usuarios en la DB para asignar como propietario de la agencia."
                )

            self.stdout.write(
                self.style.WARNING(
                    f"[*] Propietario no especificado. Asignando por defecto a: {propietario.username}"
                )
            )

        try:
            # Forzamos atomicidad: si falla la creación de canales, la agencia no se crea.
            with transaction.atomic():
                # 1. Recuperar monedas bases necesarias para la configuración regional
                try:
                    usd = Moneda.objects.get(codigo_iso="USD")
                    ves = Moneda.objects.get(codigo_iso="VES")
                except Moneda.DoesNotExist:
                    raise CommandError(
                        "[-] Error de Sistema: Las monedas base (USD/VES) deben estar pre-sembradas en la DB."
                    ) from None

                # 2. Crear la entidad maestra del Tenant
                agencia = Agencia.objects.create(
                    nombre=nombre, activa=True, propietario=propietario
                )

                # Configurar subdominio, es_sujeto_pasivo_especial y Telegram IDs
                config = agencia.configuracion
                config.subdominio_slug = subdominio
                config.es_sujeto_pasivo_especial = es_especial

                # Inyección en configuracion_api JSON para multi-tenant scalability
                config.configuracion_api = config.configuracion_api or {}
                config.configuracion_api["TELEGRAM_FINANZAS_CHAT_ID"] = tg_finanzas
                config.configuracion_api["TELEGRAM_OPERACIONES_CHAT_ID"] = tg_operaciones
                config.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"   [+] Entidad SaaS 'Agencia' creada exitosamente (ID: {agencia.pk})."
                    )
                )

                # 3. Aprovisionamiento de Canales de Recaudación Estándar (Predeterminados)
                canales_por_crear = [
                    {
                        "nombre": f"Caja Fuerte Principal (Efectivo USD) - {nombre}",
                        "tipo": CanalRecaudacion.TipoCanal.EFECTIVO,
                        "moneda": usd,
                        "descripcion": f"Custodia física de divisas en efectivo dentro de la oficina principal de {nombre}.",
                    },
                    {
                        "nombre": f"Cuenta Verde / Custodia Nacional (Bancos VES) - {nombre}",
                        "tipo": CanalRecaudacion.TipoCanal.CUSTODIA,
                        "moneda": usd,
                        "descripcion": f"Cuenta receptora de dólares de libre convertibilidad en el sistema bancario nacional de {nombre}.",
                    },
                    {
                        "nombre": f"Pago Móvil Interbancario (VES) - {nombre}",
                        "tipo": CanalRecaudacion.TipoCanal.EFECTIVO,
                        "moneda": ves,
                        "descripcion": f"Recaudación en Bolívares líquidos vía Pago Móvil para conversión inmediata a tasa BCV para {nombre}.",
                    },
                ]

                for c_data in canales_por_crear:
                    CanalRecaudacion.objects.create(
                        agencia=agencia,
                        nombre=c_data["nombre"],
                        tipo=c_data["tipo"],
                        moneda=c_data["moneda"],
                        descripcion=c_data["descripcion"],
                        activo=True,
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        "   [+] 3 Canales de Recaudación estándar vinculados e indexados de forma segura."
                    )
                )

            # Fuera del bloque transaccional: Éxito total
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[SUCCESS] Onboarding Completado con Exito!\n"
                    f"La agencia '{nombre}' ya esta operativa en la infraestructura multinacional.\n"
                    f"Resolucion de URL asignada: https://{subdominio}.travelhub.com"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    "\n[ERROR] Pipeline abortado. Se aplico ROLLBACK en la Base de Datos."
                )
            )
            raise CommandError(f"Detalles del fallo: {str(e)}") from e

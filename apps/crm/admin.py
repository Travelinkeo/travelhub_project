from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import Cliente, ComisionFreelancer, FreelancerProfile, OportunidadViaje, Pasajero


@admin.register(OportunidadViaje)
class OportunidadViajeAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ("cliente", "destino", "etapa", "creado_en")
    list_filter = ("etapa", "creado_en")
    search_fields = ("cliente__nombres", "cliente__apellidos", "destino")


@admin.register(Pasajero)
class PasajeroAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ("nombres", "apellidos", "cedula_identidad", "numero_pasaporte", "email")
    search_fields = ("nombres", "apellidos", "cedula_identidad", "numero_pasaporte", "email")
    list_filter = ("agencia",)


@admin.register(Cliente)
class ClienteAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = (
        "nombres",
        "apellidos",
        "nombre_empresa",
        "tipo_cliente",
        "telefono_principal",
        "email",
    )
    search_fields = ("nombres", "apellidos", "nombre_empresa", "email", "telefono_principal")
    list_filter = ("tipo_cliente", "es_cliente_frecuente")
    ordering = ("apellidos", "nombres")
    autocomplete_fields = ["ciudad", "pais_emision_pasaporte", "nacionalidad"]
    filter_horizontal = ("pasajeros",)


@admin.register(FreelancerProfile)
class FreelancerProfileAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = (
        "usuario",
        "agencia",
        "comision_fija_por_boleto",
        "porcentaje_comision",
        "saldo_por_cobrar",
        "activo",
    )
    list_filter = ("activo", "agencia")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name")


@admin.register(ComisionFreelancer)
class ComisionFreelancerAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = (
        "venta",
        "freelancer",
        "monto_base_venta",
        "monto_comision_ganada",
        "liquidada",
        "fecha_liquidacion",
        "creado_en",
    )
    list_filter = ("liquidada", "freelancer")
    date_hierarchy = "creado_en"
    actions = ["liquidar_comisiones"]

    @admin.action(description="Liquidar comisiones seleccionadas")
    def liquidar_comisiones(self, request, queryset):
        from django.utils import timezone
        from apps.crm.services.freelancer_service import FreelancerService

        no_liquidadas = queryset.filter(liquidada=False)
        count = no_liquidadas.count()
        if count == 0:
            self.message_user(request, "No se seleccionó ninguna comisión pendiente.")
            return

        now = timezone.now()
        freelancers_afectados = set()
        for comision in no_liquidadas:
            comision.liquidada = True
            comision.fecha_liquidacion = now
            comision.save(update_fields=["liquidada", "fecha_liquidacion"])
            freelancers_afectados.add(comision.freelancer)

        for freelancer in freelancers_afectados:
            FreelancerService.recalculate_balances(freelancer)

        self.message_user(request, f"Se han liquidado exitosamente {count} comisiones.")

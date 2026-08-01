import logging

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, UpdateView, View

from core.forms.agencia_forms import AgenciaSettingsForm, UsuarioAgenciaForm
from core.mixins import AgencyRoleRequiredMixin
from core.models.agencia import Agencia, UsuarioAgencia

logger = logging.getLogger(__name__)


class MotorPdfView(AgencyRoleRequiredMixin, UpdateView):
    """Vista para configurar el motor de identidad PDF."""

    model = Agencia
    form_class = AgenciaSettingsForm
    template_name = "core/config/motor_pdf.html"
    success_url = reverse_lazy("core:motor_pdf")
    allowed_roles = ["admin", "gerente"]

    def get_object(self, queryset=None):
        """get_object."""
        return self.request.agencia

    def form_valid(self, form):
        """form_valid."""
        messages.success(self.request, "Motor PDF actualizado correctamente.")
        return super().form_valid(form)


class AgenciaSettingsView(AgencyRoleRequiredMixin, UpdateView):
    """Vista para editar la configuración de la agencia."""

    model = Agencia
    form_class = AgenciaSettingsForm
    template_name = "core/config/agencia_settings.html"
    success_url = reverse_lazy("core:agencia_settings")
    allowed_roles = ["admin", "gerente"]

    def get_object(self, queryset=None):
        """get_object."""
        # Retorna la agencia del usuario actual de forma defensiva
        req = self.request
        agencia_obj = getattr(req, "agencia", None)

        if not agencia_obj:
            # Fallback al middleware context o asociación directa
            from core.middleware import get_current_agency

            agencia_obj = get_current_agency()

        if not agencia_obj and req.user.is_authenticated:
            # Último recurso: consulta a DB
            from core.security import get_agencia_from_request

            agencia_obj = get_agencia_from_request(req)

        if not agencia_obj:
            from django.http import Http404

            raise Http404("No tienes una agencia asignada o activa.")

        return agencia_obj

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        agencia = self.get_object()
        # La información de WhatsApp ahora se carga vía HTMX para evitar lentitud en la página principal
        context.update(
            {
                "whatsapp_status": "loading",
                "instancia": agencia.subdominio_slug,
                "AGENCIA_THEMES": Agencia.THEME_CHOICES,
                "AGENCIA_PLANTILLAS_BOLETOS": Agencia.PLANTILLAS_BOLETOS_CHOICES,
                "AGENCIA_PLANTILLAS": Agencia.PLANTILLAS_CHOICES,
            }
        )
        return context

    def form_valid(self, form):
        """form_valid."""
        logger.info(f" form_valid called for agencia: {self.get_object().nombre}")
        logger.info(f"FILES received: {dict(self.request.FILES)}")
        logger.info(f"logo_light in cleaned_data: {form.cleaned_data.get('logo_light')}")
        logger.info(f"logo_dark in cleaned_data: {form.cleaned_data.get('logo_dark')}")
        messages.success(self.request, "Configuración de agencia actualizada correctamente.")
        return super().form_valid(form)

    def form_invalid(self, form):
        """form_invalid."""
        logger.warning(f" form_invalid for agencia settings. Errors: {form.errors}")
        logger.warning(f"FILES received in invalid form: {dict(self.request.FILES)}")
        messages.error(self.request, f"Error al guardar la configuración: {form.errors}")
        return super().form_invalid(form)


class WhatsAppStatusView(AgencyRoleRequiredMixin, View):
    """Vista para cargar el estado de WhatsApp vía HTMX."""

    allowed_roles = ["admin", "gerente"]

    def get(self, request, *args, **kwargs):
        """get."""
        from django.core.cache import cache

        from apps.communications.services.evolution_api_service import EvolutionService

        # Obtener agencia de forma robusta (compatibilidad con superusuarios)
        agencia = getattr(request, "agencia", None)
        if not agencia:
            from core.security import get_agencia_from_request

            agencia = get_agencia_from_request(request)

        if not agencia:
            return HttpResponse("Configuración de agencia no encontrada.", status=404)

        session_name = agencia.subdominio_slug
        if not session_name:
            return render(
                request,
                "dashboard/partials/whatsapp_qr_new.html",
                {
                    "whatsapp_status": "error",
                    "estado": "error",
                    "qr_code": None,
                    "whatsapp_qr": None,
                },
            )

        cache_key = f"evo_qr:{session_name}"

        # 1. Verificar estado directo en Evolution API
        try:
            estado_evolution = EvolutionService.get_instance_state(session_name)
        except Exception:
            estado_evolution = "disconnected"

        # 2. Si ya está conectada, limpiar QR de Redis y retornar estado connected
        if estado_evolution == "open":
            cache.delete(cache_key)
            return render(
                request,
                "dashboard/partials/whatsapp_qr_new.html",
                {
                    "whatsapp_status": "connected",
                    "estado": "connected",
                    "qr_code": None,
                    "whatsapp_qr": None,
                    "instancia": session_name,
                },
            )

        # 3. Si la instancia está desconectada o no existe, crearla
        if estado_evolution in ("close", "disconnected"):
            try:
                result = EvolutionService.create_instance(session_name)
                if result:
                    logger.info(f"Instancia '{session_name}' auto-creada en WhatsAppStatusView")
            except Exception as e:
                logger.error(f"Error creando instancia '{session_name}': {e}")

        # 4. Intentar leer QR de Redis (Celery lo pone ahí periódicamente)
        cached_qr = cache.get(cache_key)
        if cached_qr:
            if not cached_qr.startswith("data:image"):
                cached_qr = f"data:image/png;base64,{cached_qr}"
            return render(
                request,
                "dashboard/partials/whatsapp_qr_new.html",
                {
                    "whatsapp_status": "connecting",
                    "estado": "connecting",
                    "qr_code": cached_qr,
                    "whatsapp_qr": cached_qr,
                    "instancia": session_name,
                },
            )

        # 5. Sin QR en Redis — intentar fetchearlo SINCRONAMENTE para tener garantía
        #    de devolver base64 inline (evita iframe con PNG-que-falla).
        try:
            sync_qr = EvolutionService.get_connection_qr_base64(session_name, timeout=12)
            if sync_qr:
                if not sync_qr.startswith("data:image"):
                    sync_qr = f"data:image/png;base64,{sync_qr}"
                return render(
                    request,
                    "dashboard/partials/whatsapp_qr_new.html",
                    {
                        "whatsapp_status": "connecting",
                        "estado": "connecting",
                        "qr_code": sync_qr,
                        "whatsapp_qr": sync_qr,
                        "instancia": session_name,
                    },
                )
        except Exception as e:
            logger.error(f"Error forzando fetch de QR para '{session_name}': {e}")

        # 6. Último recurso: apuntar al endpoint que sirve PNG. NO al Manager UI proxy.
        from django.urls import reverse

        try:
            manager_url = reverse("core:evolution_qr_image", kwargs={"instance_name": session_name})
        except Exception:
            manager_url = reverse("evolution_qr_image", kwargs={"instance_name": session_name})
        try:
            from apps.common.tasks import fetch_evolution_qr_task

            fetch_evolution_qr_task.delay(session_name)
        except Exception as e:
            logger.error(f"Error encolando fetch QR para '{session_name}': {e}")

        return render(
            request,
            "dashboard/partials/whatsapp_qr_new.html",
            {
                "whatsapp_status": "connecting",
                "estado": "connecting",
                "qr_code": manager_url,
                "whatsapp_qr": manager_url,
                "instancia": session_name,
            },
        )


class AgenciaUsersListView(AgencyRoleRequiredMixin, ListView):
    """Vista para listar usuarios de la agencia."""

    model = UsuarioAgencia
    template_name = "core/config/usuarios_list.html"
    context_object_name = "usuarios"
    allowed_roles = ["admin", "gerente"]

    def get_queryset(self):
        """get_queryset."""
        return UsuarioAgencia.objects.filter(agencia=self.request.agencia).select_related("usuario")


class UsuarioAgenciaCreateView(AgencyRoleRequiredMixin, View):
    """Vista para invitar/crear usuarios en la agencia."""

    allowed_roles = ["admin", "gerente"]

    def post(self, request, *args, **kwargs):
        """post."""
        agencia = request.agencia

        # Verificar límite de usuarios
        if not agencia.puede_agregar_usuario():
            messages.error(
                request,
                f"Has alcanzado el límite de usuarios de tu plan {agencia.get_plan_display()}.",
            )
            return redirect("core:agencia_usuarios")

        form = UsuarioAgenciaForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    # 1. Crear Usuario Django
                    import secrets

                    temp_password = secrets.token_urlsafe(8)

                    user = User.objects.create_user(
                        username=data["email"],
                        email=data["email"],
                        password=temp_password,
                        first_name=data["first_name"],
                        last_name=data["last_name"],
                    )

                    # 2. Crear Relación Agencia
                    UsuarioAgencia.objects.create(
                        usuario=user, agencia=agencia, rol=data["rol"], activo=True
                    )

                    messages.success(
                        request,
                        f"Usuario {data['email']} creado correctamente. Contraseña temporal: {temp_password}",
                    )

            except Exception as e:
                messages.error(request, f"Error al crear usuario: {str(e)}")
        else:
            for error in form.errors.values():
                messages.error(request, error)

        return redirect("core:agencia_usuarios")


class UsuarioAgenciaToggleStatusView(AgencyRoleRequiredMixin, View):
    """Vista HTMX para activar/desactivar usuarios."""

    allowed_roles = ["admin", "gerente"]

    def post(self, request, pk, *args, **kwargs):
        """post."""
        ua = get_object_or_404(UsuarioAgencia, pk=pk, agencia=request.agencia)

        if ua.usuario == request.user:
            return HttpResponse("No puedes desactivarte a ti mismo.", status=400)

        ua.activo = not ua.activo
        ua.save()

        status_text = "Activo" if ua.activo else "Inactivo"
        status_color = "bg-green-100 text-green-800" if ua.activo else "bg-red-100 text-red-800"

        return HttpResponse(f"""
            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {status_color}">
                {status_text}
            </span>
        """)


class UsuarioAgenciaUpdateRoleView(AgencyRoleRequiredMixin, View):
    """Vista HTMX para cambiar el rol."""

    allowed_roles = ["admin", "gerente"]

    def post(self, request, pk, *args, **kwargs):
        """post."""
        ua = get_object_or_404(UsuarioAgencia, pk=pk, agencia=request.agencia)
        new_role = request.POST.get("rol")

        if new_role not in dict(UsuarioAgencia.ROLES):
            return HttpResponse("Rol inválido", status=400)

        ua.rol = new_role
        ua.save()

        return HttpResponse(ua.get_rol_display())


class CambiarAgenciaView(View):
    """
    Permite a un usuario con múltiples agencias cambiar la agencia activa.
    Guarda la elección en la sesión para que el middleware la use.
    """

    def post(self, request, *args, **kwargs):
        """post."""
        if not request.user.is_authenticated:
            from django.http import JsonResponse

            return JsonResponse({"error": "No autenticado"}, status=401)

        agencia_id = request.POST.get("agencia_id")
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

        if not agencia_id:
            messages.error(request, _("Agencia no especificada."))
            return redirect(next_url)

        # Verificar que el usuario realmente pertenece a esa agencia
        ua = (
            UsuarioAgencia.objects.filter(
                usuario=request.user,
                agencia__id=agencia_id,
                agencia__activa=True,
                activo=True,
            )
            .select_related("agencia")
            .first()
        )

        if not ua:
            messages.error(request, _("No tienes acceso a esa agencia."))
            return redirect(next_url)

        # Guardar la elección en la sesión
        request.session["active_agencia_id"] = int(agencia_id)
        request.session.modified = True

        messages.success(request, f"Ahora estás operando en: {ua.agencia.nombre}")
        return redirect("/")

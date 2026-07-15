"""
Vistas del Wizard de Onboarding de TravelHub.

Este módulo implementa el flujo de onboarding de 5 pasos:
1. Bienvenida
2. Configuración de Agencia
3. Primer Boleto Demo
4. Invitar Teammate
5. ¡Listo!

Cada paso es una vista independiente que verifica el progreso del usuario
y redirige al paso correcto si es necesario.
"""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_POST

from apps.common.models import UserProgress
from core.models.agencia import Agencia, UsuarioAgencia

logger = logging.getLogger(__name__)
User = get_user_model()


def get_or_create_progress(user):
    """Obtiene o crea el registro de progreso del usuario."""
    progress, created = UserProgress.objects.get_or_create(
        user=user,
        defaults={
            "current_step": UserProgress.STEP_WELCOME,
            "completed_steps": [],
        },
    )
    return progress


def redirect_to_correct_step(progress):
    """Redirige al paso correcto del wizard según el progreso."""
    if progress.onboarding_completed:
        return redirect("/dashboard/")

    step_urls = {
        UserProgress.STEP_WELCOME: "onboarding_welcome",
        UserProgress.STEP_AGENCY: "onboarding_agency",
        UserProgress.STEP_FIRST_TICKET: "onboarding_first_ticket",
        UserProgress.STEP_INVITE_TEAM: "onboarding_invite_team",
        UserProgress.STEP_COMPLETE: "onboarding_complete",
    }

    next_step = progress.get_next_step()
    if next_step and next_step in step_urls:
        return redirect(reverse(step_urls[next_step]))

    return redirect("/dashboard/")


# =============================================================================
# STEP 1: BIENVENIDA
# =============================================================================


@method_decorator(login_required, name="dispatch")
class OnboardingWelcomeView(View):
    """Paso 1: Pantalla de bienvenida con overview del producto."""

    template_name = "onboarding/step1_welcome.html"

    def get(self, request):
        progress = get_or_create_progress(request.user)

        # Si ya completó este paso, saltar al siguiente
        if progress.is_step_completed(UserProgress.STEP_WELCOME):
            return redirect_to_correct_step(progress)

        context = {
            "progress": progress,
            "step": 1,
            "total_steps": 5,
            "user": request.user,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        progress = get_or_create_progress(request.user)
        progress.mark_step_completed(UserProgress.STEP_WELCOME)
        messages.success(request, _("¡Bienvenido! Continuemos configurando tu agencia."))
        return redirect(reverse("onboarding_agency"))


# =============================================================================
# STEP 2: CONFIGURACIÓN DE AGENCIA
# =============================================================================


@method_decorator(login_required, name="dispatch")
class OnboardingAgencySetupView(View):
    """Paso 2: Configuración básica de la agencia (nombre, subdominio, plan)."""

    template_name = "onboarding/step2_agency.html"

    def get(self, request):
        progress = get_or_create_progress(request.user)

        # Verificar que no haya saltado pasos
        if not progress.is_step_completed(UserProgress.STEP_WELCOME):
            return redirect(reverse("onboarding_welcome"))

        # Si ya completó este paso, saltar al siguiente
        if progress.is_step_completed(UserProgress.STEP_AGENCY):
            return redirect_to_correct_step(progress)

        # Verificar si ya tiene agencia
        agencia = Agencia.objects.filter(
            usuarios__usuario=request.user, usuarios__activo=True
        ).first()

        context = {
            "progress": progress,
            "step": 2,
            "total_steps": 5,
            "existing_agency": agencia,
            "plans": [
                {
                    "id": "FREE",
                    "name": "Free",
                    "price": "$0",
                    "features": ["1 usuario", "10 ventas/mes"],
                },
                {
                    "id": "BASIC",
                    "name": "Básico",
                    "price": "$29",
                    "features": ["3 usuarios", "100 ventas/mes"],
                },
                {
                    "id": "PRO",
                    "name": "Pro",
                    "price": "$99",
                    "features": ["10 usuarios", "Ventas ilimitadas"],
                },
            ],
        }
        return render(request, self.template_name, context)

    def post(self, request):
        progress = get_or_create_progress(request.user)

        agency_name = request.POST.get("agency_name", "").strip()
        subdomain = request.POST.get("subdomain", "").strip().lower()
        plan = request.POST.get("plan", "FREE")
        brand_color = request.POST.get("brand_color", "#3b82f6")

        # Validaciones
        errors = []
        if not agency_name:
            errors.append("El nombre de la agencia es obligatorio.")
        if not subdomain:
            errors.append("El subdominio es obligatorio.")
        if len(subdomain) < 3:
            errors.append("El subdominio debe tener al menos 3 caracteres.")
        if not subdomain.isalnum():
            errors.append("El subdominio solo puede contener letras y números.")

        # Verificar subdominio único
        if subdomain and Agencia.objects.filter(subdominio_slug=subdomain).exists():
            errors.append("Este subdominio ya está en uso.")

        if errors:
            context = {
                "progress": progress,
                "step": 2,
                "total_steps": 5,
                "error": " ".join(errors),
                "form_data": request.POST,
            }
            return render(request, self.template_name, context)

        # Crear agencia
        agencia = Agencia.objects.create(
            nombre=agency_name,
            subdominio_slug=subdomain,
            plan=plan,
            color_primario=brand_color,
        )

        # Asociar usuario a agencia
        UsuarioAgencia.objects.create(
            usuario=request.user,
            agencia=agencia,
            rol="admin",
        )

        # Actualizar límites del plan
        agencia.actualizar_limites_por_plan()

        # Marcar paso como completado
        progress.mark_step_completed(UserProgress.STEP_AGENCY)

        messages.success(request, f"¡Agencia '{agency_name}' creada exitosamente!")
        return redirect(reverse("onboarding_first_ticket"))


# =============================================================================
# STEP 3: PRIMER BOLETO DEMO
# =============================================================================


@method_decorator(login_required, name="dispatch")
class OnboardingFirstTicketView(View):
    """Paso 3: Demostración de cómo registrar un boleto."""

    template_name = "onboarding/step3_ticket.html"

    def get(self, request):
        progress = get_or_create_progress(request.user)

        # Verificar progreso
        if not progress.is_step_completed(UserProgress.STEP_AGENCY):
            return redirect(reverse("onboarding_agency"))

        if progress.is_step_completed(UserProgress.STEP_FIRST_TICKET):
            return redirect_to_correct_step(progress)

        context = {
            "progress": progress,
            "step": 3,
            "total_steps": 5,
            "demo_ticket": {
                "pasajero": "GARCIA/MARIA MR",
                "aerolinea": "AV (Avianca)",
                "ruta": "MIA → BOG → MIA",
                "fecha": "15 Jul 2026",
                "clase": "Economy",
                "precio": "$450.00",
            },
        }
        return render(request, self.template_name, context)

    def post(self, request):
        progress = get_or_create_progress(request.user)

        # En una implementación real, aquí se crearía el boleto demo
        # Por ahora, solo marcamos el paso como completado

        action = request.POST.get("action", "skip")

        if action == "demo":
            # Simular creación de boleto demo
            messages.info(
                request, _("Boleto demo registrado. En producción, esto crearía un registro real.")
            )

        progress.mark_step_completed(UserProgress.STEP_FIRST_TICKET)
        messages.success(request, _("¡Perfecto! Ahora invites a tu equipo."))
        return redirect(reverse("onboarding_invite_team"))


# =============================================================================
# STEP 4: INVITAR TEAMMATE
# =============================================================================


@method_decorator(login_required, name="dispatch")
class OnboardingInviteTeamView(View):
    """Paso 4: Invitar miembros del equipo."""

    template_name = "onboarding/step4_invite.html"

    def get(self, request):
        progress = get_or_create_progress(request.user)

        # Verificar progreso
        if not progress.is_step_completed(UserProgress.STEP_FIRST_TICKET):
            return redirect(reverse("onboarding_first_ticket"))

        if progress.is_step_completed(UserProgress.STEP_INVITE_TEAM):
            return redirect_to_correct_step(progress)

        context = {
            "progress": progress,
            "step": 4,
            "total_steps": 5,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        progress = get_or_create_progress(request.user)

        emails = request.POST.getlist("emails")
        skip = request.POST.get("skip", False)

        if not skip and emails:
            # Filtrar emails válidos
            valid_emails = [e.strip().lower() for e in emails if e.strip()]

            if valid_emails:
                # En una implementación real, aquí se enviarían invitaciones
                # Por ahora, solo mostramos un mensaje
                messages.info(
                    request,
                    f"Se enviarían invitaciones a: {', '.join(valid_emails[:3])}"
                    + (f" y {len(valid_emails) - 3} más" if len(valid_emails) > 3 else ""),
                )

        progress.mark_step_completed(UserProgress.STEP_INVITE_TEAM)
        messages.success(request, _("¡Equipo configurado!"))
        return redirect(reverse("onboarding_complete"))


# =============================================================================
# STEP 5: COMPLETADO
# =============================================================================


@method_decorator(login_required, name="dispatch")
class OnboardingCompleteView(View):
    """Paso 5: Resumen y redirect al dashboard."""

    template_name = "onboarding/step5_complete.html"

    def get(self, request):
        progress = get_or_create_progress(request.user)

        # Verificar progreso
        if not progress.is_step_completed(UserProgress.STEP_INVITE_TEAM):
            return redirect(reverse("onboarding_invite_team"))

        # Obtener info de la agencia
        agencia = Agencia.objects.filter(
            usuarios__usuario=request.user, usuarios__activo=True
        ).first()

        context = {
            "progress": progress,
            "step": 5,
            "total_steps": 5,
            "agency": agencia,
            "user": request.user,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        progress = get_or_create_progress(request.user)

        # Marcar onboarding como completado
        progress.mark_step_completed(UserProgress.STEP_COMPLETE)

        messages.success(
            request,
            _(
                "🎉 ¡Onboarding completado! Bienvenido a TravelHub. Tu agencia está lista para operar."
            ),
        )
        return redirect("/dashboard/")


# =============================================================================
# ENDPOINTS AJAX PARA PROGRESO
# =============================================================================


@login_required
def get_onboarding_progress(request):
    """API endpoint para obtener el progreso de onboarding (para HTMX/JS)."""
    progress = get_or_create_progress(request.user)

    return JsonResponse(
        {
            "completed": progress.onboarding_completed,
            "current_step": progress.current_step,
            "completed_steps": progress.completed_steps,
            "percentage": progress.get_progress_percentage(),
        }
    )


@login_required
@require_POST
def skip_onboarding(request):
    """Permite al usuario saltar el onboarding (para usuarios avanzados)."""
    progress = get_or_create_progress(request.user)

    # Marcar todos los pasos como completados
    for step in UserProgress.ALL_STEPS:
        if step not in progress.completed_steps:
            progress.completed_steps.append(step)

    progress.current_step = UserProgress.STEP_COMPLETE
    progress.save(update_fields=["completed_steps_json", "current_step", "updated_at"])

    messages.info(
        request, _("Onboarding saltado. Puedes acceder a la configuración desde el menú.")
    )
    return redirect("/dashboard/")

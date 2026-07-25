import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from core.models.agencia import Agencia, UsuarioAgencia
from core.models.onboarding import AgenciaSetupProgress
from core.security import get_agencia_from_request

logger = logging.getLogger(__name__)

STEPS_DATA = {
    "welcome": {"title": "Bienvenido a TravelHub", "subtitle": "Te guiaremos en los primeros pasos"},
    "profile": {"title": "Perfil de la Agencia", "subtitle": "Completa la información de tu agencia"},
    "team": {"title": "Invita a tu Equipo", "subtitle": "Agrega usuarios y asigna roles"},
    "fiscal": {"title": "Configuración Fiscal", "subtitle": "Define tu régimen y preferencias fiscales"},
    "done": {"title": "¡Todo Listo!", "subtitle": "Ya puedes empezar a operar"},
}


class OnboardingWizardView(LoginRequiredMixin, View):
    """Wizard de onboarding post-registro con pasos HTMX."""

    template_wrapper = "core/onboarding/wizard.html"

    def _get_agencia(self, request):
        """Método interna: get agencia."""
        return get_agencia_from_request(request)

    def _get_progress(self, agencia):
        """Método interna: get progress."""
        progress, _ = AgenciaSetupProgress.objects.get_or_create(agencia=agencia)
        return progress

    def get(self, request):
        """Método: get."""
        agencia = self._get_agencia(request)
        if not agencia:
            return redirect("core:onboarding_start")

        progress = self._get_progress(agencia)
        if progress.is_completed:
            return redirect("bookings:modern_dashboard")

        step = request.GET.get("step", progress.current_step)
        partial = request.headers.get("HX-Request") == "true"

        if partial:
            return self._render_step(request, agencia, progress, step)
        return render(request, self.template_wrapper, {
            "progress": progress,
            "steps_data": STEPS_DATA,
            "current_step": step,
            "current_step_data": STEPS_DATA.get(step, {}),
            "current_agency": agencia,
        })

    def post(self, request):
        """Método: post."""
        agencia = self._get_agencia(request)
        if not agencia:
            return HttpResponse("No hay agencia activa", status=400)

        progress = self._get_progress(agencia)
        step = request.POST.get("step", progress.current_step)
        action = request.POST.get("action", "next")

        if action == "skip":
            progress.skipped_steps = list(progress.skipped_steps) + [step]
            progress.save()
            return self._advance(progress, step, request, agencia)

        if step == "profile":
            self._save_profile(agencia, request)
        elif step == "team":
            self._save_team(agencia, request)
        elif step == "fiscal":
            self._save_fiscal(agencia, request)

        return self._advance(progress, step, request, agencia)

    def _advance(self, progress, step, request, agencia):
        """Método interna: advance."""
        next_step = self._get_next_step(step)
        progress.complete_step(step)

        if next_step == "done" or step == "done":
            return render(request, "core/onboarding/steps/done.html", {
                "current_agency": agencia,
            })

        return self._render_step(request, agencia, progress, next_step)

    def _render_step(self, request, agencia, progress, step):
        """Método interna: render step."""
        ctx = {
            "progress": progress,
            "current_step": step,
            "current_step_data": STEPS_DATA.get(step, {}),
            "current_agency": agencia,
        }
        if step == "profile":
            ctx["agencia"] = agencia
        elif step == "team":
            ctx["usuarios"] = UsuarioAgencia.objects.filter(agencia=agencia).select_related("usuario")
        elif step == "fiscal":
            from apps.finance.models import ConfiguracionFiscal
            ctx["config_fiscal"], _ = ConfiguracionFiscal.objects.get_or_create(agencia=agencia)
        return render(request, f"core/onboarding/steps/{step}.html", ctx)

    def _get_next_step(self, current):
        """Método interna: get next step."""
        steps = [s[0] for s in AgenciaSetupProgress.STEPS]
        idx = steps.index(current)
        return steps[idx + 1] if idx + 1 < len(steps) else "done"

    def _save_profile(self, agencia, request):
        """Método interna: save profile."""
        nombre_comercial = request.POST.get("nombre_comercial", "").strip()
        telefono = request.POST.get("telefono_principal", "").strip()
        direccion = request.POST.get("direccion", "").strip()
        website = request.POST.get("website", "").strip()

        if nombre_comercial:
            agencia.nombre_comercial = nombre_comercial
        if telefono:
            agencia.telefono_principal = telefono
        if direccion:
            agencia.direccion = direccion
        if website:
            agencia.website = website
        agencia.save()

    def _save_team(self, agencia, request):
        """Método interna: save team."""
        emails_raw = request.POST.get("emails", "")
        role = request.POST.get("role", "vendedor")
        from django.contrib.auth import get_user_model
        User = get_user_model()

        for email in emails_raw.split("\n"):
            email = email.strip().lower()
            if not email:
                continue
            user, _ = User.objects.get_or_create(
                email=email, defaults={"username": email, "is_active": True}
            )
            UsuarioAgencia.objects.get_or_create(
                usuario=user, agencia=agencia, defaults={"rol": role}
            )

    def _save_fiscal(self, agencia, request):
        """Método interna: save fiscal."""
        from apps.finance.models import ConfiguracionFiscal
        config, _ = ConfiguracionFiscal.objects.get_or_create(agencia=agencia)
        config.pais = request.POST.get("pais", "VEN")
        iva = request.POST.get("iva_por_defecto", "").strip()
        if iva:
            from decimal import Decimal
            config.iva_por_defecto = Decimal(iva)
        config.save()

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from core.forms.profile_forms import (
    AgencyAutomationForm,
    AgencyBasicInfoForm,
    AgencyBrandingForm,
    UserProfileForm,
)


class UserProfileView(LoginRequiredMixin, TemplateView):
    """UserProfileView."""

    template_name = "core/config/profile.html"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Obtener agencia activa de forma robusta (compatibilidad multi-tenant y superusuarios)
        agencia = getattr(self.request, "agencia", None)
        if not agencia:
            from core.security import get_agencia_from_request

            agencia = get_agencia_from_request(self.request)
        if not agencia:
            if hasattr(user, "agencias_propias") and user.agencias_propias.exists():
                agencia = user.agencias_propias.first()
            elif hasattr(user, "agencias") and user.agencias.exists():
                agencia = user.agencias.first().agencia

        context["user_form"] = UserProfileForm(instance=user)
        context["password_form"] = PasswordChangeForm(user)

        if agencia:
            context["agency_info_form"] = AgencyBasicInfoForm(instance=agencia)
            context["agency_branding_form"] = AgencyBrandingForm(instance=agencia.branding)
            context["agency_automation_form"] = AgencyAutomationForm(instance=agencia.configuracion)
            context["agencia"] = agencia

        context["active_tab"] = self.request.GET.get("tab", "perfil")
        return context

    def post(self, request, *args, **kwargs):
        """post."""
        user = request.user
        # Determinar qué formulario se envió
        form_type = request.POST.get("form_type")

        # 1. Update User Profile
        if form_type == "user_profile":
            user_form = UserProfileForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, _("Perfil actualizado correctamente."))
                return redirect(f"{reverse_lazy('core:user_profile')}?tab=perfil")
            else:
                messages.error(request, _("Error al actualizar perfil."))

        # 2. Change Password
        elif form_type == "password_change":
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important so user isn't logged out
                messages.success(request, _("Contraseña actualizada correctamente."))
                return redirect(f"{reverse_lazy('core:user_profile')}?tab=seguridad")
            else:
                for field in password_form:
                    for error in field.errors:
                        messages.error(request, f"{error}")
                return redirect(f"{reverse_lazy('core:user_profile')}?tab=seguridad")

        # 3. Agency Updates (Requires Agency)
        agencia = getattr(request, "agencia", None)
        if not agencia:
            from core.security import get_agencia_from_request

            agencia = get_agencia_from_request(request)
        if not agencia:
            if hasattr(user, "agencias_propias") and user.agencias_propias.exists():
                agencia = user.agencias_propias.first()

        if agencia:
            if form_type == "agency_info":
                info_form = AgencyBasicInfoForm(request.POST, instance=agencia)
                if info_form.is_valid():
                    info_form.save()
                    messages.success(request, _("Información de agencia actualizada."))
                    return redirect(f"{reverse_lazy('core:user_profile')}?tab=agencia")

            elif form_type == "agency_branding":
                branding_form = AgencyBrandingForm(
                    request.POST, request.FILES, instance=agencia.branding
                )
                if branding_form.is_valid():
                    branding_form.save()
                    messages.success(request, _("Branding actualizado."))
                    return redirect(f"{reverse_lazy('core:user_profile')}?tab=agencia")

            elif form_type == "agency_automation":
                automation_form = AgencyAutomationForm(request.POST, instance=agencia.configuracion)
                if automation_form.is_valid():
                    automation_form.save()
                    messages.success(request, _("Configuración de automatización guardada."))
                    return redirect(f"{reverse_lazy('core:user_profile')}?tab=automatizacion")

        messages.error(request, _("Acción no reconocida o error en formulario."))
        return redirect("core:user_profile")

from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from core.models.agencia import Agencia
from core.forms.profile_forms import UserProfileForm, AgencyBrandingForm, AgencyAutomationForm

class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'core/config/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Obtener o crear agencia del usuario (asumiendo propietario o primer agencia asignada)
        agencia = None
        if hasattr(user, 'agencias_propias') and user.agencias_propias.exists():
            agencia = user.agencias_propias.first()
        elif hasattr(user, 'agencias') and user.agencias.exists():
            agencia = user.agencias.first().agencia
            
        context['user_form'] = UserProfileForm(instance=user)
        context['password_form'] = PasswordChangeForm(user)
        
        if agencia:
            context['agency_branding_form'] = AgencyBrandingForm(instance=agencia)
            context['agency_automation_form'] = AgencyAutomationForm(instance=agencia)
            context['agencia'] = agencia
        
        context['active_tab'] = self.request.GET.get('tab', 'perfil')
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        # Determinar qué formulario se envió
        form_type = request.POST.get('form_type')
        
        # 1. Update User Profile
        if form_type == 'user_profile':
            user_form = UserProfileForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect(f"{reverse_lazy('core:user_profile')}?tab=perfil")
            else:
                messages.error(request, 'Error al actualizar perfil.')
        
        # 2. Change Password
        elif form_type == 'password_change':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important so user isn't logged out
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect(f"{reverse_lazy('core:user_profile')}?tab=seguridad")
            else:
                for field in password_form:
                    for error in field.errors:
                        messages.error(request, f"{error}")
                return redirect(f"{reverse_lazy('core:user_profile')}?tab=seguridad")

        # 3. Agency Updates (Requires Agency)
        agencia = None
        if hasattr(user, 'agencias_propias') and user.agencias_propias.exists():
            agencia = user.agencias_propias.first()
        
        if agencia:
            if form_type == 'agency_branding':
                branding_form = AgencyBrandingForm(request.POST, request.FILES, instance=agencia)
                if branding_form.is_valid():
                    branding_form.save()
                    messages.success(request, 'Configuración de agencia actualizada.')
                    return redirect(f"{reverse_lazy('core:user_profile')}?tab=agencia")
            
            elif form_type == 'agency_automation':
                automation_form = AgencyAutomationForm(request.POST, instance=agencia)
                if automation_form.is_valid():
                    automation_form.save()
                    messages.success(request, 'Configuración de automatización guardada.')
                    return redirect(f"{reverse_lazy('core:user_profile')}?tab=automatizacion")

        messages.error(request, 'Acción no reconocida o error en formulario.')
        return redirect('core:user_profile')

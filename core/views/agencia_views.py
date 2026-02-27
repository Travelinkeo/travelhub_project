from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView, ListView, CreateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.db import transaction

from core.models.agencia import Agencia, UsuarioAgencia
from core.forms.agencia_forms import AgenciaSettingsForm, UsuarioAgenciaForm
from core.mixins import AgencyRoleRequiredMixin

class AgenciaSettingsView(AgencyRoleRequiredMixin, UpdateView):
    """Vista para editar la configuración de la agencia."""
    model = Agencia
    form_class = AgenciaSettingsForm
    template_name = 'core/config/agencia_settings.html'
    success_url = reverse_lazy('core:agencia_settings')
    allowed_roles = ['admin', 'gerente']
    
    def get_object(self, queryset=None):
        # Retorna la agencia del usuario actual
        if not self.request.agencia:
            from django.http import Http404
            raise Http404("No tienes una agencia asignada.")
        return self.request.agencia

    def form_valid(self, form):
        messages.success(self.request, 'Configuración de agencia actualizada correctamente.')
        return super().form_valid(form)

class AgenciaUsersListView(AgencyRoleRequiredMixin, ListView):
    """Vista para listar usuarios de la agencia."""
    model = UsuarioAgencia
    template_name = 'core/config/usuarios_list.html'
    context_object_name = 'usuarios'
    allowed_roles = ['admin', 'gerente']
    
    def get_queryset(self):
        return UsuarioAgencia.objects.filter(agencia=self.request.agencia).select_related('usuario')

class UsuarioAgenciaCreateView(AgencyRoleRequiredMixin, View):
    """Vista para invitar/crear usuarios en la agencia."""
    allowed_roles = ['admin', 'gerente']
    
    def post(self, request, *args, **kwargs):
        agencia = request.agencia
        
        # Verificar límite de usuarios
        if not agencia.puede_agregar_usuario():
            messages.error(request, f'Has alcanzado el límite de usuarios de tu plan {agencia.get_plan_display()}.')
            return redirect('core:agencia_usuarios')
            
        form = UsuarioAgenciaForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    # 1. Crear Usuario Django
                    import secrets
                    temp_password = secrets.token_urlsafe(8)
                    
                    user = User.objects.create_user(
                        username=data['email'],
                        email=data['email'],
                        password=temp_password,
                        first_name=data['first_name'],
                        last_name=data['last_name']
                    )
                    
                    # 2. Crear Relación Agencia
                    UsuarioAgencia.objects.create(
                        usuario=user,
                        agencia=agencia,
                        rol=data['rol'],
                        activo=True
                    )
                    
                    messages.success(request, f'Usuario {data["email"]} creado correctamente. Contraseña temporal: {temp_password}')
                    
            except Exception as e:
                messages.error(request, f'Error al crear usuario: {str(e)}')
        else:
            for error in form.errors.values():
                messages.error(request, error)
                
        return redirect('core:agencia_usuarios')

class UsuarioAgenciaToggleStatusView(AgencyRoleRequiredMixin, View):
    """Vista HTMX para activar/desactivar usuarios."""
    allowed_roles = ['admin', 'gerente']
    
    def post(self, request, pk, *args, **kwargs):
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
    allowed_roles = ['admin', 'gerente']
    
    def post(self, request, pk, *args, **kwargs):
        ua = get_object_or_404(UsuarioAgencia, pk=pk, agencia=request.agencia)
        new_role = request.POST.get('rol')
        
        if new_role not in dict(UsuarioAgencia.ROLES):
            return HttpResponse("Rol inválido", status=400)

        ua.rol = new_role
        ua.save()
        
        return HttpResponse(ua.get_rol_display())

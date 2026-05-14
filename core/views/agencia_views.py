import logging
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView, View

from core.forms.agencia_forms import AgenciaSettingsForm, UsuarioAgenciaForm
from core.mixins import AgencyRoleRequiredMixin
from core.models.agencia import Agencia, UsuarioAgencia

logger = logging.getLogger(__name__)


class MotorPdfView(AgencyRoleRequiredMixin, UpdateView):
    """Vista para configurar el motor de identidad PDF."""
    model = Agencia
    form_class = AgenciaSettingsForm
    template_name = 'core/config/motor_pdf.html'
    success_url = reverse_lazy('core:motor_pdf')
    allowed_roles = ['admin', 'gerente']
    
    def get_object(self, queryset=None):
        return self.request.agencia

    def form_valid(self, form):
        messages.success(self.request, 'Motor PDF actualizado correctamente.')
        return super().form_valid(form)

class AgenciaSettingsView(AgencyRoleRequiredMixin, UpdateView):
    """Vista para editar la configuración de la agencia."""
    model = Agencia
    form_class = AgenciaSettingsForm
    template_name = 'core/config/agencia_settings.html'
    success_url = reverse_lazy('core:agencia_settings')
    allowed_roles = ['admin', 'gerente']
    
    def get_object(self, queryset=None):
        # Retorna la agencia del usuario actual de forma defensiva
        req = self.request
        agencia_obj = getattr(req, 'agencia', None)
        
        if not agencia_obj:
            # Fallback al middleware context o asociación directa
            from core.middleware import get_current_agency
            agencia_obj = get_current_agency()
            
        if not agencia_obj and req.user.is_authenticated:
            # Último recurso: consulta a DB
            ua = req.user.agencias.filter(activo=True).first()
            if ua:
                agencia_obj = ua.agencia
            
        if not agencia_obj:
            from django.http import Http404
            raise Http404("No tienes una agencia asignada o activa.")
            
        return agencia_obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agencia = self.get_object()
        # La información de WhatsApp ahora se carga vía HTMX para evitar lentitud en la página principal
        context.update({
            'whatsapp_status': 'loading',
            'instancia': agencia.subdominio_slug,
            'AGENCIA_THEMES': Agencia.THEME_CHOICES,
            'AGENCIA_PLANTILLAS_BOLETOS': Agencia.PLANTILLAS_BOLETOS_CHOICES,
            'AGENCIA_PLANTILLAS': Agencia.PLANTILLAS_CHOICES,
        })
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Configuración de agencia actualizada correctamente.')
        return super().form_valid(form)

class WhatsAppStatusView(AgencyRoleRequiredMixin, View):
    """Vista para cargar el estado de WhatsApp vía HTMX."""
    allowed_roles = ['admin', 'gerente']
    
    def get(self, request, *args, **kwargs):
        from apps.communications.services.whatsapp_unified import WhatsAppService
        
        # Obtener agencia de forma robusta (compatibilidad con superusuarios)
        agencia = getattr(request, 'agencia', None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            agencia = ua.agencia if ua else None
            
        if not agencia:
            return HttpResponse("Configuración de agencia no encontrada.", status=404)
            
        session_name = agencia.subdominio_slug

        
        # Timeout corto para no bloquear HTMX demasiado
        try:
            # Obtener estado de WhatsApp
            estado_raw = WhatsAppService.get_status(session_name)
            
            # Mapeo a estados UI
            estado_ui = 'disconnected'
            if estado_raw == 'WORKING':
                estado_ui = 'connected'
            elif estado_raw == 'CONNECTING':
                estado_ui = 'connecting'
                
            qr_code = None
            if estado_ui != 'connected':
                # Solo intentamos QR si no estamos conectados
                qr_code = WhatsAppService.get_qr_code(session_name)
                
                if not qr_code:
                    # Intento de arranque defensivo
                    WhatsAppService.start_session(session_name)
                    qr_code = WhatsAppService.get_qr_code(session_name)
                
                if qr_code:
                    estado_ui = 'connecting'
        except Exception as e:
            logger.error(f"Error en WhatsAppStatusView: {e}")
            estado_ui = 'error'
            qr_code = None

        return render(request, 'dashboard/partials/whatsapp_qr_new.html', {
            'whatsapp_status': estado_ui,
            'estado': estado_ui,
            'qr_code': qr_code,
            'whatsapp_qr': qr_code,
            'instancia': session_name,
        })

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

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from core.models import Agencia, AuditLog
from core.mixins import AgencyRoleRequiredMixin

class AgenciaAuditLogListView(AgencyRoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'gerente']
    model = AuditLog
    template_name = 'core/audit/audit_list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        # Aseguramos que tenemos la agencia (el mixin ya valida validación, pero por seguridad)
        agencia = getattr(self.request, 'agencia', None)
        if not agencia:
            return AuditLog.objects.none()

        # Filtrar logs relacionados con esta agencia.
        # Estrategia:
        # 1. Logs vinculados a Ventas de esta agencia (venta__agencia=agencia)
        # 2. Logs creados por Usuarios de esta agencia (user__agencias__agencia=agencia)
        
        # Nota: El punto 2 es más costoso y podría traer ruido si un usuario pertenece a varias agencias 
        # (caso raro en SaaS puro, pero posible en admin).
        # Por ahora, nos centramos en logs de Ventas de la agencia + Logs donde el usuario es de la agencia.

        queryset = AuditLog.objects.filter(
            Q(venta__agencia=agencia) | 
            Q(user__agencias__agencia=agencia, user__agencias__activo=True)
        ).select_related('user', 'venta').order_by('-creado')

        # Filtros opcionales del frontend
        q_search = self.request.GET.get('q')
        if q_search:
            queryset = queryset.filter(
                Q(descripcion__icontains=q_search) |
                Q(user__first_name__icontains=q_search) |
                Q(user__last_name__icontains=q_search) |
                Q(user__email__icontains=q_search) |
                Q(object_id__icontains=q_search)
            )

        usuario_id = self.request.GET.get('usuario')
        if usuario_id:
            queryset = queryset.filter(user_id=usuario_id)

        accion = self.request.GET.get('accion')
        if accion:
            queryset = queryset.filter(accion=accion)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasar lista de usuarios de la agencia para el filtro
        if self.request.agencia:
            context['usuarios_agencia'] = self.request.agencia.usuarios.filter(activo=True).select_related('usuario')
        return context

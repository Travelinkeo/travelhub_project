from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from core.models.agencia import Agencia, UsuarioAgencia
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

class GodModeDashboardView(UserPassesTestMixin, View):
    """
    Dashboard Global para el dueño de la plataforma (Armando).
    Solo accesible por superusuarios.
    """
    template_name = "god_mode/dashboard.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        # 1. Platform Metrics
        total_agencias = Agencia.objects.count()
        agencias_activas = Agencia.objects.filter(activa=True).count()
        total_usuarios = User.objects.count()
        
        # 2. Financial Metrics (Estimadas por planes)
        # Esto es una simplificación, en producción vendría de transacciones reales de Stripe
        revenue_mensual = Agencia.objects.filter(plan='BASIC').count() * 29 + \
                         Agencia.objects.filter(plan='PRO').count() * 99 + \
                         Agencia.objects.filter(plan='ENTERPRISE').count() * 299
        
        # 3. Growth
        last_30_days = timezone.now() - timedelta(days=30)
        nuevas_agencias_30d = Agencia.objects.filter(fecha_creacion__gte=last_30_days).count()

        # 4. Agency List (Top 20 más recientes)
        agencias = Agencia.objects.all().order_by('-fecha_creacion')[:20]

        # 5. Plan Distribution
        plan_dist = Agencia.objects.values('plan').annotate(count=Count('id'))

        context = {
            'metrics': {
                'total_agencias': total_agencias,
                'agencias_activas': agencias_activas,
                'total_usuarios': total_usuarios,
                'revenue_mensual': revenue_mensual,
                'nuevas_30d': nuevas_agencias_30d,
            },
            'agencias': agencias,
            'plan_dist': plan_dist,
        }
        return render(request, self.template_name, context)

class ImpersonateAgencyView(UserPassesTestMixin, View):
    """
    Permite al SuperAdmin "entrar" como administrador de una agencia específica.
    """
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, agencia_id, *args, **kwargs):
        # En una implementación real, esto cambiaría una variable de sesión o 
        # usaría un backend de autenticación que permita impersonation.
        # Por ahora, redirigimos al dashboard de esa agencia (si el middleware lo permite)
        # Pero el middleware de context depende del usuario. 
        # Una forma común es asignar el usuario de esa agencia temporalmente a la sesión.
        
        # TODO: Implementar lógica de impersonation segura
        return redirect('core:modern_dashboard')

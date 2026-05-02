from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from core.models.agencia import Agencia, UsuarioAgencia
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from apps.bookings.models import BoletoImportado
import logging

logger = logging.getLogger(__name__)


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
        # revenue_mensual = Agencia.objects.filter(plan='BASIC').count() * 29 + \
        #                  Agencia.objects.filter(plan='PRO').count() * 99 + \
        #                  Agencia.objects.filter(plan='ENTERPRISE').count() * 299
        revenue_mensual = 0
        
        # 3. Growth
        last_30_days = timezone.now() - timedelta(days=30)
        nuevas_agencias_30d = Agencia.objects.filter(fecha_creacion__gte=last_30_days).count()

        # 4. Agency List (Top 20 más recientes)
        agencias = Agencia.objects.all().order_by('-fecha_creacion')[:20]

        # 5. Plan Distribution
        plan_dist = Agencia.objects.values('plan').annotate(count=Count('id'))

        # 6. Global Activity (Real)
        ultimos_boletos = BoletoImportado.all_objects.select_related('agencia').order_by('-fecha_subida')[:5]
        nuevas_agencias = Agencia.objects.order_by('-fecha_creacion')[:5]
        
        # Activity feed (Reconstructed)
        actividad = []
        
        for b in ultimos_boletos:
            actividad.append({
                'titulo': 'Boleto Procesado',
                'detalle': f'Boleto {b.localizador_pnr} subido por {b.agencia.nombre if b.agencia else "Desconocida"}',
                'fecha': b.fecha_subida,
                'color': 'blue'
            })
            
        for a in nuevas_agencias:
            actividad.append({
                'titulo': 'Nueva Agencia Onboarded',
                'detalle': f'Agencia {a.nombre} se unió a la plataforma.',
                'fecha': a.fecha_creacion,
                'color': 'emerald'
            })
            
        # Sort activity by date
        actividad = sorted(actividad, key=lambda x: x['fecha'], reverse=True)

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
            'actividad': actividad[:10],
        }

        return render(request, self.template_name, context)

class ImpersonateAgencyView(UserPassesTestMixin, View):
    """
    Permite al SuperAdmin "entrar" como administrador de una agencia específica.
    """
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, agencia_id, *args, **kwargs):
        """
        Activa el modo impersonación para una agencia específica.
        """
        try:
            agencia = Agencia.objects.get(id=agencia_id)
            
            # Guardamos el ID en la sesión
            request.session['impersonated_agencia_id'] = str(agencia.id)
            request.session['impersonated_agencia_name'] = agencia.nombre
            
            logger.info(f"👤 SuperAdmin {request.user.username} impersonando a la agencia: {agencia.nombre}")
            
            # Redirigimos al dashboard moderno (que ahora mostrará los datos de esa agencia)
            return redirect('core:modern_dashboard')
            
        except Agencia.DoesNotExist:
            return redirect('god_mode')

class StopImpersonateView(UserPassesTestMixin, View):
    """
    Detiene el modo impersonación y vuelve al contexto de SuperAdmin.
    """
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        if 'impersonated_agencia_id' in request.session:
            del request.session['impersonated_agencia_id']
        if 'impersonated_agencia_name' in request.session:
            del request.session['impersonated_agencia_name']
            
        return redirect('god_mode')

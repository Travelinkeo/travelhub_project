from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from core.models.agencia import Agencia, UsuarioAgencia
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from apps.bookings.models import BoletoImportado
from apps.bookings.models import HotelTarifario, TipoHabitacion
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
        from core.models.ai import AIUsageLog
        from apps.finance.models.reconciliacion import ConciliacionBoleto
        
        # 1. Platform Metrics
        total_agencias = Agencia.objects.count()
        agencias_activas_objs = Agencia.objects.filter(activa=True)
        agencias_activas = agencias_activas_objs.count()
        total_usuarios = User.objects.count()
        
        # 2. Sales Metrics (Global)
        from apps.bookings.models import Venta, VentaAuditFinding
        total_ventas = Venta.all_objects.count()
        volumen_ventas = Venta.all_objects.aggregate(total=Sum('total_venta'))['total'] or 0
        hallazgos_criticos = VentaAuditFinding.all_objects.filter(estado='PEN').count()

        # 3. Financial Metrics (Real MRR calculation)
        plan_prices = {
            'FREE': 0,
            'BASIC': 29,
            'PRO': 99,
            'ENTERPRISE': 299
        }
        revenue_mensual = 0
        for ag in agencias_activas_objs:
            revenue_mensual += plan_prices.get(ag.plan, 0)
        
        # 4. Growth & AI Usage (Last 24h)
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_30_days = now - timedelta(days=30)
        
        nuevas_agencias_30d = Agencia.objects.filter(fecha_creacion__gte=last_30_days).count()
        ai_usage_24h = AIUsageLog.objects.filter(timestamp__gte=last_24h).count()
        
        # 5. Financial Leakage (Sum of all discrepancies across all agencies)
        leakage_data = ConciliacionBoleto.all_objects.aggregate(total=Sum('diferencia_total'))
        total_leakage = leakage_data['total'] or 0
        
        # 6. Global Inventory Metrics
        total_hoteles = HotelTarifario.all_objects.count()
        total_habitaciones = TipoHabitacion.objects.count() # No usa AgenciaMixin

        # 7. Agency List (Top 20 más recientes)
        agencias = Agencia.objects.all().order_by('-fecha_creacion')[:20]

        # 8. Plan Distribution
        plan_dist = Agencia.objects.values('plan').annotate(count=Count('id'))

        # 9. Global Activity (Real)
        ultimos_boletos = BoletoImportado.all_objects.select_related('agencia').order_by('-fecha_subida')[:5]
        nuevas_agencias = Agencia.objects.order_by('-fecha_creacion')[:5]
        ultimos_ai_logs = AIUsageLog.objects.select_related('agencia').order_by('-timestamp')[:5]
        
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

        for log in ultimos_ai_logs:
            actividad.append({
                'titulo': f'IA: {log.feature}',
                'detalle': f'Modelo {log.model_name} usado por {log.agencia.nombre if log.agencia else "Global"}. Estado: {log.status}',
                'fecha': log.timestamp,
                'color': 'purple' if log.status == 'SUCCESS' else 'red'
            })
            
        # Sort activity by date
        actividad = sorted(actividad, key=lambda x: x['fecha'], reverse=True)

        context = {
            'metrics': {
                'total_agencias': total_agencias,
                'agencias_activas': agencias_activas,
                'total_usuarios': total_usuarios,
                'total_ventas': total_ventas,
                'volumen_ventas': volumen_ventas,
                'hallazgos_criticos': hallazgos_criticos,
                'revenue_mensual': revenue_mensual,
                'nuevas_30d': nuevas_agencias_30d,
                'ai_usage_24h': ai_usage_24h,
                'total_leakage': total_leakage,
                'total_hoteles': total_hoteles,
                'total_habitaciones': total_habitaciones,
            },
            'agencias': agencias,
            'plan_dist': plan_dist,
            'actividad': actividad[:15],
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

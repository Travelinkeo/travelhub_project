import logging
from datetime import timedelta

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from apps.bookings.models import BoletoImportado, HotelTarifario, TipoHabitacion
from core.models.agencia import Agencia
from core.models.audit import AuditLog, crear_audit_log
from core.views.health_views import _check_celery, _check_database, _check_disk, _check_redis

logger = logging.getLogger(__name__)

GOD_MODE_TIMEOUT = 1800
GOD_MODE_MAX_IMPERSONATIONS = 5
GOD_MODE_RATE_WINDOW = 3600


class GodModeDashboardView(UserPassesTestMixin, View):
    template_name = "god_mode/dashboard.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        from apps.finance.models.reconciliacion import ConciliacionBoleto
        from core.models.ai import AIUsageLog

        total_agencias = Agencia.objects.count()
        agencias_activas_objs = Agencia.objects.filter(activa=True)
        agencias_activas = agencias_activas_objs.count()
        total_usuarios = User.objects.count()

        from apps.bookings.models import Venta, VentaAuditFinding
        total_ventas = Venta.all_objects.count()
        volumen_ventas = Venta.all_objects.aggregate(total=Sum('total_venta'))['total'] or 0
        hallazgos_criticos = VentaAuditFinding.all_objects.filter(estado='PEN').count()

        plan_prices = {
            'FREE': 0,
            'BASIC': 29,
            'PRO': 99,
            'ENTERPRISE': 299
        }
        revenue_mensual = 0
        for ag in agencias_activas_objs:
            revenue_mensual += plan_prices.get(ag.plan, 0)

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_30_days = now - timedelta(days=30)

        nuevas_agencias_30d = Agencia.objects.filter(fecha_creacion__gte=last_30_days).count()
        ai_usage_24h = AIUsageLog.objects.filter(timestamp__gte=last_24h).count()

        leakage_data = ConciliacionBoleto.all_objects.aggregate(total=Sum('diferencia_total'))
        total_leakage = leakage_data['total'] or 0

        total_hoteles = HotelTarifario.all_objects.count()
        total_habitaciones = TipoHabitacion.objects.count()

        agencias = Agencia.objects.all().order_by('-fecha_creacion')[:20]
        plan_dist = Agencia.objects.values('plan').annotate(count=Count('id'))

        ultimos_boletos = BoletoImportado.all_objects.select_related('agencia').order_by('-fecha_subida')[:5]
        nuevas_agencias = Agencia.objects.order_by('-fecha_creacion')[:5]
        ultimos_ai_logs = AIUsageLog.objects.select_related('agencia').order_by('-timestamp')[:5]

        # Impersonation audit log
        impersonation_logs = AuditLog.objects.filter(
            accion='IMPERSONATE'
        ).order_by('-creado')[:20]

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
                'detalle': f'Agencia {a.nombre} se unio a la plataforma.',
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

        actividad = sorted(actividad, key=lambda x: x['fecha'], reverse=True)

        system_status = {
            "database": _check_database(),
            "redis": _check_redis(),
            "celery": _check_celery(),
            "disk": _check_disk(),
        }
        system_ok = all(v.get("ok") for v in system_status.values())

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
            'impersonation_logs': impersonation_logs,
            'system_status': system_status,
            'system_ok': system_ok,
        }

        return render(request, self.template_name, context)


class ImpersonateAgencyView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, agencia_id, *args, **kwargs):
        user = request.user

        rate_key = f"god_mode:impersonate:{user.pk}"
        count = cache.get(rate_key, 0)
        if count >= GOD_MODE_MAX_IMPERSONATIONS:
            logger.warning(f"God Mode rate limit exceeded for {user.username}")
            return HttpResponseForbidden(
                "Has excedido el limite de impersonaciones. Intenta de nuevo en 1 hora."
            )

        try:
            agencia = Agencia.objects.get(id=agencia_id)

            request.session['impersonated_agencia_id'] = str(agencia.id)
            request.session['impersonated_agencia_name'] = agencia.nombre
            request.session['impersonated_at'] = timezone.now().isoformat()

            crear_audit_log(
                modelo='Agencia',
                object_id=str(agencia.id),
                accion=AuditLog.Accion.LOGIN,
                venta=None,
                agencia=agencia,
                user=user,
                descripcion=f"SuperAdmin {user.username} inicio impersonacion de {agencia.nombre}",
                metadata_extra={'action': 'impersonate_start', 'target_agencia_id': agencia.id},
            )

            cache.set(rate_key, count + 1, timeout=GOD_MODE_RATE_WINDOW)
            logger.info(f"SuperAdmin {user.username} impersonando a: {agencia.nombre}")

            return redirect('core:modern_dashboard')

        except Agencia.DoesNotExist:
            return redirect('god_mode')


class StopImpersonateView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        if 'impersonated_agencia_id' in request.session:
            agencia_id = request.session['impersonated_agencia_id']
            agencia_name = request.session.get('impersonated_agencia_name', 'Desconocida')

            crear_audit_log(
                modelo='Agencia',
                object_id=str(agencia_id),
                accion=AuditLog.Accion.LOGOUT,
                venta=None,
                user=request.user,
                descripcion=f"SuperAdmin {request.user.username} finalizo impersonacion de {agencia_name}",
                metadata_extra={'action': 'impersonate_stop', 'target_agencia_id': agencia_id},
            )

            del request.session['impersonated_agencia_id']
            del request.session['impersonated_agencia_name']
            del request.session['impersonated_at']

        return redirect('god_mode')

import logging
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count
from django.utils import timezone
from apps.crm.models import FreelancerProfile, ComisionFreelancer

from apps.finance.models import LinkDePago

logger = logging.getLogger(__name__)

class FreelancerDashboardView(LoginRequiredMixin, View):
    template_name = 'crm/freelancer/dashboard.html'

    def get(self, request, *args, **kwargs):
        # Validar que el usuario logueado tenga un perfil de Freelancer
        if not hasattr(request.user, 'perfil_freelancer'):
            logger.warning(f"Usuario {request.user.username} intentó acceder al portal freelancer sin perfil.")
            return redirect('core:modern_dashboard') # Redirigir al panel normal

        freelancer = request.user.perfil_freelancer
        
        # 1. Métricas Rápidas (Agregaciones ORM optimizadas)
        mes_actual = timezone.now().month
        
        comisiones_mes = ComisionFreelancer.objects.filter(
            freelancer=freelancer, 
            creado_en__month=mes_actual
        ).aggregate(
            total=Sum('monto_comision_ganada'),
            cantidad=Count('id')
        )
        
        # 2. Las últimas 10 ventas del Freelancer
        ultimas_comisiones = ComisionFreelancer.objects.filter(
            freelancer=freelancer
        ).select_related('venta', 'venta__cliente').order_by('-creado_en')[:10]
        
        # 3. Links de Pago Pendientes (De las ventas asociadas al freelancer)
        links_pendientes = LinkDePago.objects.filter(
            venta__comision_asignada__freelancer=freelancer,
            estado='PEN'
        ).select_related('venta').order_by('-creado_en')[:5]

        context = {
            'freelancer': freelancer,
            'comision_mes_actual': comisiones_mes['total'] or 0.0,
            'ventas_mes_actual': comisiones_mes['cantidad'] or 0,
            'ultimas_ventas': ultimas_comisiones,
            'links_pendientes': links_pendientes,
        }
        return render(request, self.template_name, context)

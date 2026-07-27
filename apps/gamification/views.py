import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from core.api import get_agencia_from_request

from .models import Logro, LogroProgreso, Nivel, PuntuacionUsuario

logger = logging.getLogger(__name__)


class GamificationDashboardView(LoginRequiredMixin, View):
    """Dashboard principal de gamificación con logros, puntuación, y ranking."""

    template_name = "gamification/dashboard.html"

    def get(self, request):
        """get."""
        agencia = get_agencia_from_request(request)
        if not agencia:
            return render(request, self.template_name, {"sin_agencia": True})

        usuario = request.user

        puntuacion, _ = PuntuacionUsuario.objects.get_or_create(
            usuario=usuario,
            agencia=agencia,
        )
        niveles = list(Nivel.objects.all().order_by("puntos_minimos"))
        siguiente_nivel = None
        for _i, nivel in enumerate(niveles):
            if nivel.puntos_minimos > puntuacion.puntos_total:
                siguiente_nivel = nivel
                break

        progresos = (
            LogroProgreso.objects.filter(
                usuario=usuario,
                agencia=agencia,
            )
            .select_related("logro")
            .order_by("-completado", "-progreso")
        )

        logros_ids_completados = set(
            progresos.filter(completado=True).values_list("logro_id", flat=True)
        )
        logros_disponibles = Logro.objects.filter(activo=True).exclude(
            id__in=logros_ids_completados
        )

        ranking = (
            PuntuacionUsuario.objects.filter(agencia=agencia)
            .select_related("usuario", "nivel")
            .order_by("-puntos_total")[:20]
        )

        ctx = {
            "puntuacion": puntuacion,
            "siguiente_nivel": siguiente_nivel,
            "niveles": niveles,
            "progresos": progresos,
            "logros_disponibles": logros_disponibles,
            "ranking": ranking,
            "current_agency": agencia,
        }
        return render(request, self.template_name, ctx)


class GamificationBadgesView(LoginRequiredMixin, View):
    """Lista visual de todos los logros (conquistados y por conquistar)."""

    template_name = "gamification/badges.html"

    def get(self, request):
        """get."""
        agencia = get_agencia_from_request(request)
        if not agencia:
            return render(request, self.template_name, {"sin_agencia": True})

        progresos = LogroProgreso.objects.filter(
            usuario=request.user,
            agencia=agencia,
        ).select_related("logro")

        completados = [p for p in progresos if p.completado]
        pendientes = [p for p in progresos if not p.completado]

        sin_iniciar = Logro.objects.filter(activo=True).exclude(
            id__in=[p.logro_id for p in progresos]
        )

        ctx = {
            "completados": completados,
            "pendientes": pendientes,
            "sin_iniciar": sin_iniciar,
            "current_agency": agencia,
        }
        return render(request, self.template_name, ctx)


class GamificationLeaderboardView(LoginRequiredMixin, View):
    """Ranking de la agencia."""

    template_name = "gamification/leaderboard.html"

    def get(self, request):
        """get."""
        agencia = get_agencia_from_request(request)
        if not agencia:
            return render(request, self.template_name, {"sin_agencia": True})

        ranking = (
            PuntuacionUsuario.objects.filter(agencia=agencia)
            .select_related("usuario", "nivel")
            .order_by("-puntos_total")
        )

        ctx = {
            "ranking": ranking,
            "current_agency": agencia,
        }
        return render(request, self.template_name, ctx)

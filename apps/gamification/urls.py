"""Configuración de rutas (URLs) para la aplicación gamification.
"""

from django.urls import path

from . import views

app_name = "gamification"

urlpatterns = [
    path("", views.GamificationDashboardView.as_view(), name="dashboard"),
    path("badges/", views.GamificationBadgesView.as_view(), name="badges"),
    path("leaderboard/", views.GamificationLeaderboardView.as_view(), name="leaderboard"),
]

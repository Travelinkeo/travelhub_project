"""
URLs del Wizard de Onboarding de TravelHub.

Este módulo define las rutas para los 5 pasos del wizard:
1. /onboarding/wizard/ - Bienvenida
2. /onboarding/wizard/agency/ - Configuración de Agencia
3. /onboarding/wizard/ticket/ - Primer Boleto Demo
4. /onboarding/wizard/invite/ - Invitar Teammate
5. /onboarding/wizard/complete/ - ¡Listo!
"""

from django.urls import path

from apps.common.views.onboarding_views import (
    OnboardingAgencySetupView,
    OnboardingCompleteView,
    OnboardingFirstTicketView,
    OnboardingInviteTeamView,
    OnboardingWelcomeView,
    get_onboarding_progress,
    skip_onboarding,
)

urlpatterns = [
    # Wizard Steps
    path(
        "wizard/",
        OnboardingWelcomeView.as_view(),
        name="onboarding_welcome",
    ),
    path(
        "wizard/agency/",
        OnboardingAgencySetupView.as_view(),
        name="onboarding_agency",
    ),
    path(
        "wizard/ticket/",
        OnboardingFirstTicketView.as_view(),
        name="onboarding_first_ticket",
    ),
    path(
        "wizard/invite/",
        OnboardingInviteTeamView.as_view(),
        name="onboarding_invite_team",
    ),
    path(
        "wizard/complete/",
        OnboardingCompleteView.as_view(),
        name="onboarding_complete",
    ),
    # API Endpoints
    path(
        "progress/",
        get_onboarding_progress,
        name="onboarding_progress",
    ),
    path(
        "skip/",
        skip_onboarding,
        name="onboarding_skip",
    ),
]

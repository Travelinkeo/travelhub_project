import logging

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .base import AgenciaMixin

logger = logging.getLogger(__name__)


class AgenciaSetupProgress(AgenciaMixin):
    """AgenciaSetupProgress."""

    STEPS = [
        ("welcome", _("Bienvenida")),
        ("profile", _("Perfil de Agencia")),
        ("team", _("Tu Equipo")),
        ("fiscal", _("Configuración Fiscal")),
        ("done", _("¡Todo Listo!")),
    ]

    current_step = models.CharField(max_length=20, choices=STEPS, default="welcome")
    completed_steps = models.JSONField(default=list, blank=True)
    skipped_steps = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Progreso de Onboarding")
        verbose_name_plural = _("Progresos de Onboarding")

    def __str__(self):
        """__str__."""
        return f"Agencia {self.agencia_id}: {self.get_current_step_display()} ({'completado' if self.is_completed else 'en progreso'})"

    def complete_step(self, step):
        """Marca un paso como completado."""
        if step not in self.completed_steps:
            self.completed_steps = list(self.completed_steps) + [step]
        steps_order = [s[0] for s in self.STEPS]
        current_idx = steps_order.index(step)
        if current_idx + 1 < len(steps_order):
            self.current_step = steps_order[current_idx + 1]
        else:
            self.current_step = "done"
            self.is_completed = True
            self.completed_at = timezone.now()
        self.save()

from django.db import models


class FeatureFlag(models.Model):
    """
    Feature flags para activar/desactivar funcionalidades sin deploy.

    Soporta:
    - Flags globales (agencia=None): afectan a toda la plataforma
    - Flags por agencia: rollout gradual o acceso beta
    - Rollout porcentual (0-100): activacion progresiva para % de agencias
    """

    nombre = models.CharField(max_length=100, db_index=True)
    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Null = flag global. Con agencia = flag por tenant.",
    )
    enabled = models.BooleanField(default=False)
    rollout_percentage = models.IntegerField(
        default=100,
        help_text="0-100. Solo aplica si enabled=True y agencia=None.",
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("nombre", "agencia")]
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"

    def __str__(self):
        scope = "GLOBAL" if self.agencia is None else self.agencia.nombre
        return f"{self.nombre} ({scope})"

    @classmethod
    def is_enabled(cls, name, agencia=None, default=False):
        """
        Verifica si un feature flag esta activo.

        Orden de prioridad:
        1. Flag por agencia (si existe)
        2. Flag global con rollout
        3. default
        """
        if agencia:
            flag = cls.objects.filter(nombre=name, agencia=agencia).first()
            if flag is not None:
                return flag.enabled

        flag = cls.objects.filter(nombre=name, agencia=None).first()
        if flag is None:
            return default
        if not flag.enabled:
            return False
        if flag.rollout_percentage >= 100:
            return True
        if agencia:
            hash_val = hash(f"{name}:{agencia.id}") % 100
            return hash_val < flag.rollout_percentage
        return True

import json

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import validar_no_vacio_o_espacios


class UserProgress(models.Model):
    """UserProgress."""

    STEP_WELCOME = "welcome"
    STEP_AGENCY = "agency"
    STEP_FIRST_TICKET = "first_ticket"
    STEP_INVITE_TEAM = "invite_team"
    STEP_COMPLETE = "complete"

    ALL_STEPS: list[str] = [
        STEP_WELCOME,
        STEP_AGENCY,
        STEP_FIRST_TICKET,
        STEP_INVITE_TEAM,
        STEP_COMPLETE,
    ]

    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="onboarding_progress"
    )
    current_step = models.CharField(max_length=20, default=STEP_WELCOME)
    completed_steps_json = models.TextField(default="[]", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Progreso de Onboarding"
        verbose_name_plural = "Progresos de Onboarding"

    @property
    def completed_steps(self) -> list[str]:
        return json.loads(self.completed_steps_json)

    @completed_steps.setter
    def completed_steps(self, value: list[str]) -> None:
        """completed_steps."""
        self.completed_steps_json = json.dumps(value)

    @property
    def onboarding_completed(self) -> bool:
        return self.current_step == self.STEP_COMPLETE

    def mark_step_completed(self, step: str) -> None:
        """mark_step_completed."""
        if step not in self.ALL_STEPS:
            raise ValueError(f"Paso inválido: {step}")
        steps = self.completed_steps
        if step not in steps:
            steps.append(step)
        self.completed_steps = steps
        next_idx = self.ALL_STEPS.index(step) + 1
        self.current_step = (
            self.ALL_STEPS[next_idx] if next_idx < len(self.ALL_STEPS) else self.STEP_COMPLETE
        )
        self.save(update_fields=["completed_steps_json", "current_step"])

    def is_step_completed(self, step: str) -> bool:
        """is_step_completed."""
        return step in self.completed_steps

    def reset(self) -> None:
        """Reinicia el progreso de onboarding a su estado inicial."""
        self.completed_steps = []
        self.current_step = self.STEP_WELCOME
        self.save(update_fields=["completed_steps_json", "current_step", "updated_at"])

    def get_next_step(self) -> str | None:
        """get_next_step."""
        if self.onboarding_completed:
            return None
        for step in self.ALL_STEPS:
            if step not in self.completed_steps:
                return step
        return None

    def get_progress_percentage(self) -> int:
        """get_progress_percentage."""
        completed = len(self.completed_steps)
        total = len(self.ALL_STEPS)
        return int((completed / total) * 100)

    def __str__(self) -> str:
        """__str__."""
        status = "Completado" if self.onboarding_completed else f"{self.get_progress_percentage()}%"
        return f"Onboarding {self.user} - {status}"


class Pais(models.Model):
    """Pais."""

    id_pais = models.AutoField(primary_key=True, verbose_name=_("ID País"))
    codigo_iso_2 = models.CharField(
        _("Código ISO 2"),
        max_length=2,
        unique=True,
        help_text=_("Código ISO 3166-1 alfa-2 del país."),
    )
    codigo_iso_3 = models.CharField(
        _("Código ISO 3"),
        max_length=3,
        unique=True,
        help_text=_("Código ISO 3166-1 alfa-3 del país."),
    )
    nombre = models.CharField(
        _("Nombre del País"), max_length=100, unique=True, validators=[validar_no_vacio_o_espacios]
    )

    class Meta:
        verbose_name = _("País")
        verbose_name_plural = _("Países")
        ordering = ["nombre"]

    def __str__(self) -> str:
        """__str__."""
        return self.nombre


class Ciudad(models.Model):
    """Ciudad."""

    id_ciudad = models.AutoField(primary_key=True, verbose_name=_("ID Ciudad"))
    nombre = models.CharField(
        _("Nombre de la Ciudad"), max_length=100, validators=[validar_no_vacio_o_espacios]
    )
    codigo_iata = models.CharField(
        _("Código IATA"),
        max_length=3,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Código IATA de 3 letras de la ciudad o aeropuerto."),
    )
    pais = models.ForeignKey(
        Pais, on_delete=models.PROTECT, verbose_name=_("País"), null=True, blank=True
    )
    region_estado = models.CharField(_("Región/Estado"), max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = _("Ciudad")
        verbose_name_plural = _("Ciudades")
        ordering = ["pais__nombre", "nombre"]
        unique_together = ("nombre", "pais", "region_estado")

    def __str__(self) -> str:
        """__str__."""
        return f"{self.nombre}{f', {self.region_estado}' if self.region_estado else ''} ({self.pais.nombre})"


class Aerolinea(models.Model):
    """Aerolinea."""

    id_aerolinea = models.AutoField(primary_key=True, verbose_name=_("ID Aerolínea"))
    codigo_iata = models.CharField(
        _("Código IATA"),
        max_length=3,
        blank=True,
        help_text=_("Código IATA de 2 letras de la aerolínea (ej. AA, AV, LA)."),
    )
    codigo_numerico = models.CharField(
        _("Código Numérico/Placa"),
        max_length=3,
        blank=True,
        null=True,
        help_text=_("Código numérico de 3 dígitos asignado por IATA (ej. 134, 052)"),
    )
    codigo_icao = models.CharField(
        _("Código ICAO"), max_length=3, blank=True, help_text=_("Código ICAO de 3 letras")
    )
    nombre = models.CharField(
        _("Nombre de la Aerolínea"), max_length=150, validators=[validar_no_vacio_o_espacios]
    )
    orden_prioridad = models.IntegerField(
        _("Orden de Prioridad"), default=100, help_text=_("Para mostrar al principio en listas.")
    )
    pais_origen = models.CharField(_("País de Origen"), max_length=100, blank=True)
    rif = models.CharField(
        _("RIF"),
        max_length=20,
        blank=True,
        help_text=_("RIF venezolano o E-99999999-X para internacionales"),
    )
    activa = models.BooleanField(
        _("Activa"), default=True, help_text=_("Indica si la aerolínea está actualmente operando.")
    )

    class Meta:
        verbose_name = _("Aerolínea")
        verbose_name_plural = _("Aerolíneas")
        ordering = ["nombre"]

    def __str__(self) -> str:
        """__str__."""
        return f"{self.nombre} ({self.codigo_iata})"


# --- MODELO MOVIDO DESDE FINANCE ---
class Moneda(models.Model):
    """Moneda."""

    id_moneda = models.AutoField(primary_key=True, verbose_name=_("ID Moneda"))
    codigo_iso = models.CharField(
        _("Código ISO"),
        max_length=3,
        unique=True,
        help_text=_("Código ISO 4217 de la moneda (ej. USD, EUR, VEF)."),
    )
    nombre = models.CharField(
        _("Nombre de la Moneda"),
        max_length=50,
        unique=True,
        validators=[validar_no_vacio_o_espacios],
    )
    simbolo = models.CharField(_("Símbolo"), max_length=5, blank=True, null=True)
    es_moneda_local = models.BooleanField(
        _("Es Moneda Local"),
        default=False,
        help_text=_("Marcar si esta es la moneda principal de la agencia."),
    )

    class Meta:
        verbose_name = _("Moneda")
        verbose_name_plural = _("Monedas")
        ordering = ["nombre"]
        # Edited 2026-06-07: changed from "finance_moneda" to "core_moneda" to
        # match the actual table name in DB. core.0001_initial creates the table
        # as `core_moneda` (default app_label+model_name) and that's what prod
        # uses too. The previous value was inconsistent with reality and broke
        # fresh-DB migrations because AlterField on Moneda tried to reference
        # a non-existent `finance_moneda` table.
        db_table = "core_moneda"

    def __str__(self) -> str:
        """__str__."""
        return f"{self.nombre} ({self.codigo_iso})"

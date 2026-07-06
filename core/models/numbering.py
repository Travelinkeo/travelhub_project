"""
Modelo de secuencia numérica atómica con ORM puro.

Reemplaza pg_advisory_xact_lock con select_for_update() sobre
una fila de lock única por prefijo.
"""

from django.db import models


class NumberingSequence(models.Model):
    """Fila de lock para numeración secuencial atómica vía ORM.

    Cada prefijo (ej: 'F-20260608', 'AS-20260608') tiene una fila única.
    El lock se adquiere con select_for_update() dentro de una transacción.
    """

    prefix = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Prefijo de numeración",
        help_text="Prefijo único (ej: F-20260608, AS-20260608).",
    )
    last_number = models.IntegerField(
        default=0,
        verbose_name="Último número usado",
        help_text="Último sufijo numérico asignado para este prefijo.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        verbose_name = "Secuencia numérica"
        verbose_name_plural = "Secuencias numéricas"
        db_table = "core_numbering_sequence"

    def __str__(self):
        return f"{self.prefix}-{self.last_number:04d}"

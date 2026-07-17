from django.db import models

from core.models.agencia import Agencia


class AIUsageLog(models.Model):
    """
    Tracks AI API consumption across the platform.
    """

    MODELS = [
        ("gemini-1.5-pro", "Gemini 1.5 Pro"),
        ("gemini-2.5-flash", "Gemini 1.5 Flash"),
        ("gemini-2.5-flash-8b", "Gemini 1.5 Flash 8B"),
        ("imagen-3", "Imagen 3"),
    ]

    agencia = models.ForeignKey(
        Agencia, on_delete=models.CASCADE, null=True, blank=True, related_name="ai_logs"
    )
    model_name = models.CharField(max_length=50, choices=MODELS)
    feature = models.CharField(
        max_length=100
    )  # 'ticket_parsing', 'reconciliation', 'marketing_copy', etc.
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, default="SUCCESS")  # SUCCESS, FAILED, 429_LIMIT

    class Meta:
        verbose_name = "Log de Uso de IA"
        verbose_name_plural = "Logs de Uso de IA"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.agencia or 'Global'} - {self.feature} - {self.timestamp}"

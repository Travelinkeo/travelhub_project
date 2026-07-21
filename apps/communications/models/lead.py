from django.db import models


class Lead(models.Model):
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150, blank=True, default="")
    fuente = models.CharField(max_length=50, default="landing_page")
    ip_origen = models.CharField(max_length=45, blank=True, default="")
    guia_descargada = models.BooleanField(default=False)
    email_enviado = models.BooleanField(default=False)
    _followup_1_sent = models.BooleanField(default=False)
    _followup_2_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

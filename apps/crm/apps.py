"""Configuración de la aplicación Django crm.
"""

from django.apps import AppConfig


class CrmConfig:
    """Configuración de crm. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"
    label = "crm"
    verbose_name = "CRM (Clientes y Pasajeros)"

# contabilidad/apps.py
from django.apps import AppConfig


class ContabilidadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contabilidad'
    verbose_name = 'Contabilidad VEN-NIF'
    
    def ready(self):
        """Importar señales al iniciar la aplicación"""
        import contabilidad.signals  # noqa

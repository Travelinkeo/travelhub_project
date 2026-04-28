from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Configuración de inicialización del core.
        Inyecta comportamientos dinámicos (Monkeypatching) cuando la app está lista.
        """
        from django.contrib.auth.models import User
        from .utils import user_monkeypatch
        
        # Inyectar propiedad 'agencia' al modelo User nativo de Django
        # Esto permite hacer: request.user.agencia sin necesidad de un perfil separado
        User.add_to_class('agencia', property(user_monkeypatch.get_user_agency))
        User.add_to_class('rol_agencia', property(user_monkeypatch.get_user_role))


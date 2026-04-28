from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test


class IsStaffOrGroupWrite(permissions.BasePermission):
    """Lectura (SAFE_METHODS) permitida a usuarios autenticados.
    Escritura solo a staff o miembros de grupos cuyo nombre contenga
    alguno de los keywords permitidos (por defecto: 'oper', 'venta').
    """
    allowed_group_keywords = ['oper', 'venta']

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.is_staff:
            return True
        user_group_names = [g.name.lower() for g in user.groups.all()]
        return any(any(kw in name for kw in self.allowed_group_keywords) for name in user_group_names)

def rol_requerido(nombres_grupos):
    """
    Escudo de intercepción. Verifica si el operativo pertenece 
    a los grupos autorizados antes de procesar la petición.
    """
    def check_group(user):
        if user.is_active and (user.is_superuser or user.groups.filter(name__in=nombres_grupos).exists()):
            return True
        raise PermissionDenied("Brecha de seguridad detectada: Nivel de autorización insuficiente.")
    return user_passes_test(check_group)

__all__ = ["IsStaffOrGroupWrite", "rol_requerido"]

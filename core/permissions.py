from rest_framework import permissions


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

__all__ = ["IsStaffOrGroupWrite"]

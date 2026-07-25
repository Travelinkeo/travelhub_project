"""Módulo api de la aplicación crm.
"""

from rest_framework import permissions, viewsets

from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin

from .models import Cliente, Pasajero
from .serializers import ClienteSerializer, PasajeroSerializer


class ClienteViewSet:
    """Clase ClienteViewSet. Uso: según contexto de la aplicación.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]


class PasajeroViewSet:
    """Clase PasajeroViewSet. Uso: según contexto de la aplicación.
    """
    queryset = Pasajero.objects.all()
    serializer_class = PasajeroSerializer
    permission_classes = [permissions.IsAuthenticated]

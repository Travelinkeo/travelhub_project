from rest_framework import permissions, viewsets

from core.api.mixins.tenant import TenantViewSetMixin

from .models import Cliente, Pasajero
from .serializers import ClienteSerializer, PasajeroSerializer


class ClienteViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]

class PasajeroViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Pasajero.objects.all()
    serializer_class = PasajeroSerializer
    permission_classes = [permissions.IsAuthenticated]

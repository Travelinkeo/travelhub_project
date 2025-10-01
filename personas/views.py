from rest_framework import viewsets, filters
from .models import Cliente, Pasajero
from .serializers import ClienteSerializer, PasajeroSerializer

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    throttle_classes = []  # Desactivar rate limiting para esta vista
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombres', 'apellidos', 'cedula_identidad', 'nombre_empresa', 'email']

class PasajeroViewSet(viewsets.ModelViewSet):
    queryset = Pasajero.objects.all()
    serializer_class = PasajeroSerializer

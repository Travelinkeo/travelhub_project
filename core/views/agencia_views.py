"""Views para gestión de Agencia."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from core.models import Agencia, UsuarioAgencia
from core.serializers import (
    AgenciaSerializer, UsuarioAgenciaSerializer, 
    CrearUsuarioAgenciaSerializer, UsuarioSerializer
)


class AgenciaViewSet(viewsets.ModelViewSet):
    """ViewSet para Agencia."""
    
    queryset = Agencia.objects.all()
    serializer_class = AgenciaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Filtrar por agencias del usuario
        user = self.request.user
        if user.is_superuser:
            return Agencia.objects.all()
        return Agencia.objects.filter(usuarios__usuario=user, usuarios__activo=True)
    
    def perform_create(self, serializer):
        serializer.save(propietario=self.request.user)
    
    @action(detail=True, methods=['get'])
    def usuarios(self, request, pk=None):
        """Listar usuarios de la agencia."""
        agencia = self.get_object()
        usuarios = UsuarioAgencia.objects.filter(agencia=agencia)
        serializer = UsuarioAgenciaSerializer(usuarios, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def agregar_usuario(self, request, pk=None):
        """Crear y agregar usuario a la agencia."""
        agencia = self.get_object()
        serializer = CrearUsuarioAgenciaSerializer(data=request.data)
        
        if serializer.is_valid():
            # Crear usuario
            user = User.objects.create_user(
                username=serializer.validated_data['username'],
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', '')
            )
            
            # Asignar a agencia
            usuario_agencia = UsuarioAgencia.objects.create(
                usuario=user,
                agencia=agencia,
                rol=serializer.validated_data['rol']
            )
            
            return Response(
                UsuarioAgenciaSerializer(usuario_agencia).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def asignar_usuario_existente(self, request, pk=None):
        """Asignar usuario existente a la agencia."""
        agencia = self.get_object()
        user_id = request.data.get('usuario_id')
        rol = request.data.get('rol', 'vendedor')
        
        try:
            user = User.objects.get(id=user_id)
            usuario_agencia, created = UsuarioAgencia.objects.get_or_create(
                usuario=user,
                agencia=agencia,
                defaults={'rol': rol}
            )
            
            if not created:
                usuario_agencia.activo = True
                usuario_agencia.rol = rol
                usuario_agencia.save()
            
            return Response(
                UsuarioAgenciaSerializer(usuario_agencia).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )


class UsuarioAgenciaViewSet(viewsets.ModelViewSet):
    """ViewSet para UsuarioAgencia."""
    
    queryset = UsuarioAgencia.objects.all()
    serializer_class = UsuarioAgenciaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return UsuarioAgencia.objects.all()
        return UsuarioAgencia.objects.filter(agencia__usuarios__usuario=user)

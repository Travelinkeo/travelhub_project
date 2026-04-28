from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import AuditLog
from ..serializers import AuditLogSerializer

class AuditLogListView(APIView):
    """
    Vista para consultar los logs de auditoría filtrados por modelo y ID de objeto.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        modelo = request.query_params.get('modelo')
        object_id = request.query_params.get('object_id')
        venta_id = request.query_params.get('venta_id')
        
        logs = AuditLog.objects.all().order_by('-creado')
        
        if modelo:
            logs = logs.filter(modelo=modelo)
        if object_id:
            logs = logs.filter(object_id=str(object_id))
        if venta_id:
            logs = logs.filter(venta_id=venta_id)
            
        serializer = AuditLogSerializer(logs[:100], many=True)
        return Response(serializer.data)

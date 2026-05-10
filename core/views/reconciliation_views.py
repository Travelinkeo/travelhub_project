import logging
import io
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.http import HttpResponse

from core.services.supplier_reconciliation_service import SupplierReconciliationService

logger = logging.getLogger(__name__)

class SupplierReconciliationAPIView(APIView):
    """
    API endpoint para procesar reportes de proveedores (PDF o Excel)
    y conciliarlos contra la base de datos de TravelHub.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No se proporcionó ningún archivo.'}, status=status.HTTP_400_BAD_REQUEST)
        
        filename = file_obj.name.lower()
        provider_id = request.data.get('provider_id') # Opcional
        
        # Determinar el tipo de agencia actual para Multi-tenancy
        agencia = None
        if hasattr(request, 'agencia'):
            agencia = request.agencia
        
        service = SupplierReconciliationService(agencia=agencia)
        results = None

        try:
            if filename.endswith('.pdf'):
                # Utilizar la IA para extraer y conciliar
                results = service.reconcile_from_pdf_ia(file_obj, filename, provider_id)
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                # Usar pandas directo
                results = service.reconcile_from_excel(file_obj, provider_id)
            else:
                return Response({'error': 'Formato de archivo no soportado. Use PDF o Excel.'}, status=status.HTTP_400_BAD_REQUEST)

            if results is None:
                return Response({'error': 'Hubo un problema al procesar el archivo o la extracción falló.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Si el cliente solicita exportar directamente a Excel:
            if request.data.get('export_excel') == 'true':
                output = io.BytesIO()
                success = service.export_results_to_excel(results, output)
                if success:
                    output.seek(0)
                    response = HttpResponse(
                        output.read(), 
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="conciliacion_{filename}.xlsx"'
                    return response
                else:
                    return Response({'error': 'Fallo al generar el archivo Excel.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Retornar JSON
            return Response({
                'message': 'Conciliación completada exitosamente',
                'results': results,
                'total_records': len(results),
                'discrepancies_count': sum(1 for r in results if r['status'] == 'DISCREPANCY'),
                'not_found_count': sum(1 for r in results if r['status'] == 'NOT_FOUND_INTERNALLY'),
                'ok_count': sum(1 for r in results if r['status'] == 'OK')
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error procesando conciliación: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class SupplierReconciliationUIView(LoginRequiredMixin, TemplateView):
    template_name = 'finance/supplier_reconciliation.html'

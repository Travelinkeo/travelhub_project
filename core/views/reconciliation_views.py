import io
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.services.supplier_reconciliation_service import SupplierReconciliationService
from core.auth_helpers import InternalAPIAuthMixin

logger = logging.getLogger(__name__)


@extend_schema(
    description="Procesar reportes de proveedores (PDF o Excel) y conciliarlos contra la base de datos de TravelHub.\n\n"
    "Soporta extracción por IA (PDF) y pandas (Excel) con exportación opcional a Excel.",
    request={
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary",
                        "description": "Archivo PDF o Excel del proveedor",
                    },
                    "provider_id": {
                        "type": "string",
                        "description": "ID opcional del proveedor para pre-filtrar",
                    },
                    "export_excel": {
                        "type": "boolean",
                        "description": "Si es true, descarga el resultado como Excel en lugar de JSON",
                    },
                },
                "required": ["file"],
            }
        }
    },
    responses={
        200: {"description": "Resultados de conciliación con conteo de discrepancias"},
        400: {"description": "Formato no soportado o archivo faltante"},
    },
    tags=["Conciliación"],
)
class SupplierReconciliationAPIView(InternalAPIAuthMixin, APIView):
    """
    API endpoint para procesar reportes de proveedores (PDF o Excel)
    y conciliarlos contra la base de datos de TravelHub.
    """

    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"error": "No se proporcionó ningún archivo."}, status=status.HTTP_400_BAD_REQUEST
            )

        filename = file_obj.name.lower()
        provider_id = request.data.get("provider_id")  # Opcional

        # Determinar el tipo de agencia actual para Multi-tenancy
        agencia = None
        if hasattr(request, "agencia"):
            agencia = request.agencia

        service = SupplierReconciliationService(agencia=agencia)
        results = None

        try:
            if filename.endswith(".pdf"):
                # Utilizar la IA para extraer y conciliar
                results = service.reconcile_from_pdf_ia(file_obj, filename, provider_id)
            elif filename.endswith(".xlsx") or filename.endswith(".xls"):
                # Usar pandas directo
                results = service.reconcile_from_excel(file_obj, provider_id)
            else:
                return Response(
                    {"error": "Formato de archivo no soportado. Use PDF o Excel."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if results is None:
                return Response(
                    {"error": "Hubo un problema al procesar el archivo o la extracción falló."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Si el cliente solicita exportar directamente a Excel:
            if request.data.get("export_excel") == "true":
                output = io.BytesIO()
                success = service.export_results_to_excel(results, output)
                if success:
                    output.seek(0)
                    response = HttpResponse(
                        output.read(),
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    response["Content-Disposition"] = (
                        f'attachment; filename="conciliacion_{filename}.xlsx"'
                    )
                    return response
                else:
                    return Response(
                        {"error": "Fallo al generar el archivo Excel."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Retornar JSON
            return Response(
                {
                    "message": "Conciliación completada exitosamente",
                    "results": results,
                    "total_records": len(results),
                    "discrepancies_count": sum(1 for r in results if r["status"] == "DISCREPANCY"),
                    "not_found_count": sum(
                        1 for r in results if r["status"] == "NOT_FOUND_INTERNALLY"
                    ),
                    "ok_count": sum(1 for r in results if r["status"] == "OK"),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error procesando conciliación: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierReconciliationUIView(LoginRequiredMixin, TemplateView):
    template_name = "finance/supplier_reconciliation.html"

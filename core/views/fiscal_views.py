from datetime import datetime
from django.http import HttpResponse
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.finance.services.libro_compras import LibroComprasService
from apps.finance.services.retenciones_xml import RetencionesXMLService

class LibroComprasViewSet(viewsets.ViewSet):
    """ViewSet para generar Libro de Compras"""

    authentication_classes = [SessionAuthentication, JWTAuthentication, TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def generar(self, request):
        """
        Genera el libro de compras para un período

        Query params:
            - fecha_inicio: YYYY-MM-DD
            - fecha_fin: YYYY-MM-DD
            - formato: json|csv (default: json)
        """
        fecha_inicio_str = request.query_params.get("fecha_inicio")
        fecha_fin_str = request.query_params.get("fecha_fin")
        formato = request.query_params.get("formato", "json")

        if not fecha_inicio_str or not fecha_fin_str:
            return Response(
                {"error": "Se requieren fecha_inicio y fecha_fin (formato: YYYY-MM-DD)"}, status=400
            )

        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=400)

        # Generar libro de compras para la agencia del usuario
        agencia = request.user.agencia
        libro_compras = LibroComprasService.generar_libro_compras(fecha_inicio, fecha_fin, agencia=agencia)

        if formato == "csv":
            csv_content = LibroComprasService.exportar_csv(libro_compras)
            response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
            filename = f"libro_compras_{fecha_inicio_str}_{fecha_fin_str}.csv"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        return Response(libro_compras)


class RetencionesXMLViewSet(viewsets.ViewSet):
    """ViewSet para descargar XML de Retenciones para SENIAT"""

    authentication_classes = [SessionAuthentication, JWTAuthentication, TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def descargar_xml(self, request):
        """
        Descarga el archivo XML de Retenciones de ISLR para el portal del SENIAT

        Query params:
            - fecha_inicio: YYYY-MM-DD
            - fecha_fin: YYYY-MM-DD
        """
        fecha_inicio_str = request.query_params.get("fecha_inicio")
        fecha_fin_str = request.query_params.get("fecha_fin")

        if not fecha_inicio_str or not fecha_fin_str:
            return Response(
                {"error": "Se requieren fecha_inicio y fecha_fin (formato: YYYY-MM-DD)"}, status=400
            )

        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=400)

        agencia = request.user.agencia
        xml_content = RetencionesXMLService.generar_xml_retenciones(fecha_inicio, fecha_fin, agencia=agencia)

        response = HttpResponse(xml_content, content_type="application/xml; charset=utf-8")
        filename = f"retenciones_islr_{agencia.rif or 'agencia'}_{fecha_inicio.strftime('%Y%m')}.xml"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

import io
import json
from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from apps.finance.services.supplier_reconciliation_service import SupplierReconciliationService

from .models import CuentaContable
from .reportes import ReportesContables

"""
Vistas para reportes contables en el admin.
"""

# Instancia global del agente para mantener el hilo de la conversación (opcional)
# Para producción real, se debería persistir el historial por usuario/sesión.
_agent_instance = None


def get_agent():
    global _agent_instance
    if _agent_instance is None:
        from django.utils.module_loading import import_string

        TravelHubAgent = import_string("apps.automation.services.ai_agent.TravelHubAgent")
        _agent_instance = TravelHubAgent()
    return _agent_instance


@staff_member_required
def reporte_balance_comprobacion(request):
    """Vista para Balance de Comprobación"""

    # Fechas por defecto: mes actual
    hoy = date.today()
    fecha_desde = request.GET.get("desde", hoy.replace(day=1))
    fecha_hasta = request.GET.get("hasta", hoy)
    moneda = request.GET.get("moneda", "USD")

    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)

    resultado = ReportesContables.balance_comprobacion(fecha_desde, fecha_hasta, moneda)

    return render(
        request,
        "contabilidad/balance_comprobacion.html",
        {
            "resultado": resultado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "moneda": moneda,
        },
    )


@staff_member_required
def reporte_estado_resultados(request):
    """Vista para Estado de Resultados"""

    hoy = date.today()
    fecha_desde = request.GET.get("desde", hoy.replace(day=1))
    fecha_hasta = request.GET.get("hasta", hoy)
    moneda = request.GET.get("moneda", "USD")

    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)

    resultado = ReportesContables.estado_resultados(fecha_desde, fecha_hasta, moneda)

    return render(
        request,
        "contabilidad/estado_resultados.html",
        {
            "resultado": resultado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "moneda": moneda,
        },
    )


@staff_member_required
def reporte_balance_general(request):
    """Vista para Balance General"""

    hoy = date.today()
    fecha_corte = request.GET.get("fecha", hoy)
    moneda = request.GET.get("moneda", "USD")

    if isinstance(fecha_corte, str):
        fecha_corte = date.fromisoformat(fecha_corte)

    resultado = ReportesContables.balance_general(fecha_corte, moneda)

    return render(
        request,
        "contabilidad/balance_general.html",
        {"resultado": resultado, "fecha_corte": fecha_corte, "moneda": moneda},
    )


@staff_member_required
def reporte_libro_diario(request):
    """Vista para Libro Diario"""

    hoy = date.today()
    fecha_desde = request.GET.get("desde", hoy.replace(day=1))
    fecha_hasta = request.GET.get("hasta", hoy)
    moneda = request.GET.get("moneda", "USD")

    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)

    asientos = ReportesContables.libro_diario(fecha_desde, fecha_hasta, moneda)

    return render(
        request,
        "contabilidad/libro_diario.html",
        {
            "asientos": asientos,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "moneda": moneda,
        },
    )


@staff_member_required
def reporte_libro_mayor(request):
    """Vista para Libro Mayor"""

    cuenta_id = request.GET.get("cuenta")
    if not cuenta_id:
        # Mostrar selector de cuenta
        cuentas = CuentaContable.objects.filter(acepta_movimientos=True).order_by("codigo")
        return render(request, "contabilidad/libro_mayor_selector.html", {"cuentas": cuentas})

    hoy = date.today()
    fecha_desde = request.GET.get("desde", hoy.replace(day=1))
    fecha_hasta = request.GET.get("hasta", hoy)
    moneda = request.GET.get("moneda", "USD")

    if isinstance(fecha_desde, str):
        fecha_desde = date.fromisoformat(fecha_desde)
    if isinstance(fecha_hasta, str):
        fecha_hasta = date.fromisoformat(fecha_hasta)

    resultado = ReportesContables.libro_mayor(int(cuenta_id), fecha_desde, fecha_hasta, moneda)

    return render(
        request,
        "contabilidad/libro_mayor.html",
        {
            "resultado": resultado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "moneda": moneda,
        },
    )


@staff_member_required
def assistant_brain_view(request):
    """Vista para el Asistente AI 'Brain'"""
    return render(request, "contabilidad/assistant.html")


@staff_member_required
def api_assistant_chat(request):
    """API para el chat del asistente Brain"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            if data.get("clear"):
                request.session["ai_assistant_history"] = []
                request.session.modified = True
                return JsonResponse({"status": "history cleared"})

            user_message = data.get("message", "")
            if not user_message:
                return JsonResponse({"error": "No message provided"}, status=400)

            # Obtener el historial de la sesión para evitar pérdida de contexto en multi-procesos
            session_history = request.session.get("ai_assistant_history", [])
            agent = get_agent()
            agent.history = session_history

            response_text = agent.process_query(user_message)

            # Guardar el historial actualizado en la sesión
            request.session["ai_assistant_history"] = agent.history
            request.session.modified = True

            return JsonResponse(
                {
                    "response": response_text,
                    "data_found": True,
                }
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@staff_member_required
def reconciliation_view(request):
    """Vista para cargar reportes de proveedores y conciliarlos."""
    if request.method == "POST" and request.FILES.get("reporte"):
        reporte = request.FILES["reporte"]
        provider_id = request.POST.get("proveedor")

        service = SupplierReconciliationService()

        # Determinar si es Excel o PDF
        if reporte.name.endswith((".xlsx", ".xls")):
            results = service.reconcile_from_excel(reporte, provider_id)
        elif reporte.name.endswith(".pdf"):
            # Para PDF usamos el método IA
            results = service.reconcile_from_pdf_ia(reporte, reporte.name, provider_id)
        else:
            return render(
                request, "contabilidad/reconciliation.html", {"error": "Formato no soportado."}
            )

        if results is None:
            return render(
                request,
                "contabilidad/reconciliation.html",
                {"error": "Error procesando el archivo."},
            )

        # Serializar resultados para el botón de exportar
        results_json = json.dumps(results, default=str)

        return render(
            request,
            "contabilidad/reconciliation_results.html",
            {"results": results, "results_json": results_json, "filename": reporte.name},
        )

    return render(request, "contabilidad/reconciliation.html")


@staff_member_required
def export_reconciliation_results(request):
    """Exporta los resultados de la conciliación a Excel."""
    if request.method == "POST":
        results_json = request.POST.get("results_json")
        if results_json:
            try:
                results = json.loads(results_json)
                service = SupplierReconciliationService()

                output = io.BytesIO()
                if service.export_results_to_excel(results, output):
                    output.seek(0)
                    response = HttpResponse(
                        output.read(),
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    response["Content-Disposition"] = (
                        f'attachment; filename="conciliacion_{date.today()}.xlsx"'
                    )
                    return response
            except Exception as e:
                return HttpResponse(f"Error exportando: {str(e)}", status=500)

    return HttpResponse("Solicitud inválida", status=400)

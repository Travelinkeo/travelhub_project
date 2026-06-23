import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.generic import TemplateView, View
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.models import PropuestaTransaccionIA
from apps.finance.models.reconciliacion import ConciliacionBoleto
from apps.finance.serializers import PropuestaTransaccionIASerializer
from core.auth_helpers import InternalAPIAuthMixin

logger = logging.getLogger(__name__)


class AIAccountingDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "finance/accounting_assistant.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ua = self.request.user.agencias.filter(activo=True).first()
        context["user_agencia"] = ua.agencia if ua else None
        return context


class AIAccountingChatView(InternalAPIAuthMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "ai_parser_quota"

    def post(self, request):
        """
        Endpoint para interactuar con el Asistente Financiero.
        Payload: {"message": "Pregunta del usuario"}
        """
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Mensaje requerido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check Agency Context
            agencia = getattr(request, "agencia", None)
            if not agencia:
                ua = request.user.agencias.filter(activo=True).first()
                if ua:
                    agencia = ua.agencia

            if not agencia:
                return Response(
                    {"error": "No tienes una agencia activa asociada."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            from apps.finance.services.ai_accounting_service import AIAccountingService

            service = AIAccountingService(agencia)
            response_text = service.ask(user_message)

            return Response({"response": response_text, "agency": agencia.nombre})

        except Exception as e:
            logger.exception("Error en AI Chat View")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIChatHTMXView(LoginRequiredMixin, View):
    """
    Versión para HTMX del Chat AI que retorna fragmentos HTML.
    """

    def post(self, request):
        user_message = request.POST.get("message")
        if not user_message:
            return HttpResponse("", status=400)

        agencia = getattr(request, "agencia", None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            if ua:
                agencia = ua.agencia

        if not agencia:
            return render(
                request,
                "finance/partials/ai_chat_message.html",
                {
                    "role": "assistant",
                    "content": "No tienes una agencia activa asociada para realizar consultas financieras.",
                },
            )

        try:
            # Usamos el servicio robusto y unificado de Contabilidad
            from apps.finance.services.ai_accounting_service import AIAccountingService

            service = AIAccountingService(agencia)
            response_text = service.ask(user_message)

            return render(
                request,
                "finance/partials/ai_chat_message.html",
                {"role": "assistant", "content": response_text},
            )

        except Exception as e:
            logger.exception("Error en AI Chat HTMX")
            return render(
                request,
                "finance/partials/ai_chat_message.html",
                {"role": "assistant", "content": f"Error técnico: {str(e)}"},
            )


class ResolveDiscrepancyAIView(InternalAPIAuthMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "ai_parser_quota"

    def get(self, request, pk):
        """
        Analiza una discrepancia financiera usando el Asistente Contable AI.
        Retorna un fragmento de HTML para ser inyectado por HTMX.
        """
        conciliacion = get_object_or_404(ConciliacionBoleto, pk=pk)
        linea = conciliacion.linea_reporte
        boleto = conciliacion.boleto_local

        agencia = getattr(request, "agencia", None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            if ua:
                agencia = ua.agencia

        if not agencia:
            return render(
                request,
                "finance/reconciliation/partials/ai_analysis_error.html",
                {"error": "No hay agencia activa asociada."},
            )

        try:
            from apps.finance.services.ai_accounting_service import AIAccountingService

            assistant = AIAccountingService(agencia)

            boleto_num = linea.numero_boleto_reportado if linea else "N/A"
            explicacion = assistant.ask(
                f"Analiza la discrepancia del boleto {boleto_num} y explicame que paso."
            )

            propuesta_json = assistant.propose_accounting_entry("Boleto", conciliacion.pk)
            import json

            propuesta = json.loads(propuesta_json)

            context = {
                "conciliacion": conciliacion,
                "linea": linea,
                "boleto": boleto,
                "explicacion": explicacion,
                "propuesta": propuesta,
            }
            return render(request, "finance/reconciliation/partials/ai_analysis.html", context)

        except Exception as e:
            logger.exception(f"Error analizando discrepancia {pk}")
            return render(
                request,
                "finance/reconciliation/partials/ai_analysis_error.html",
                {"error": f"Error técnico: {str(e)}"},
            )


class PropuestaTransaccionIAListCreateAPIView(InternalAPIAuthMixin, generics.ListCreateAPIView):
    serializer_class = PropuestaTransaccionIASerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "ai_parser_quota"

    def get_queryset(self):
        agencia = getattr(self.request, "agencia", None)
        if not agencia:
            ua = self.request.user.agencias.filter(activo=True).first()
            if ua:
                agencia = ua.agencia
        if not agencia:
            return PropuestaTransaccionIA.objects.none()
        return PropuestaTransaccionIA.objects.filter(agencia=agencia)

    def perform_create(self, serializer):
        agencia = getattr(self.request, "agencia", None)
        if not agencia:
            ua = self.request.user.agencias.filter(activo=True).first()
            if ua:
                agencia = ua.agencia
        if not agencia:
            raise ValidationError("No tienes una agencia activa asociada.")
        serializer.save(agencia=agencia)


class ResolvePropuestaAPIView(InternalAPIAuthMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "ai_parser_quota"

    def post(self, request, pk, action):
        """
        Resuelve una propuesta de transacción IA (aprobar/rechazar).
        action: 'approve' o 'reject'
        """
        agencia = getattr(request, "agencia", None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            if ua:
                agencia = ua.agencia

        if not agencia:
            return Response(
                {"error": "No tienes una agencia activa asociada."},
                status=status.HTTP_403_FORBIDDEN,
            )

        propuesta = get_object_or_404(PropuestaTransaccionIA, pk=pk, agencia=agencia)

        if propuesta.estado != PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE:
            return Response(
                {"error": "Esta propuesta ya fue resuelta anteriormente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comentarios = request.data.get("comentarios", "")

        if action == "reject":
            propuesta.estado = PropuestaTransaccionIA.EstadoPropuesta.RECHAZADA
            propuesta.fecha_resolucion = timezone.now()
            propuesta.usuario_resolutor = request.user
            propuesta.comentarios_resolucion = comentarios or "Rechazado manualmente por el CFO."
            propuesta.save()
            return Response(
                {
                    "status": "propuesta_rechazada",
                    "message": f"La propuesta {pk} ha sido rechazada exitosamente.",
                }
            )

        elif action == "approve":
            try:
                payload = propuesta.payload_datos

                # Ejecutar de forma determinista y transaccional
                if propuesta.accion_tipo == "CONCILIAR_REPORTE":
                    report_id = payload.get("report_id")
                    if not report_id:
                        raise ValidationError("El payload no contiene 'report_id'.")

                    # Lanzar tarea de Celery
                    from django.db import transaction

                    from apps.finance.tasks_reconciliation import conciliar_reporte_batch_task

                    transaction.on_commit(
                        lambda: conciliar_reporte_batch_task.delay(report_id, agencia.pk)
                    )

                    execution_msg = f"La reconciliación del reporte {report_id} se ha enviado a Celery para procesamiento asíncrono seguro."

                elif propuesta.accion_tipo == "CREAR_ASIENTO":
                    from decimal import Decimal

                    from django.apps import apps
                    from django.db import transaction

                    AsientoContable = apps.get_model("contabilidad", "AsientoContable")
                    DetalleAsiento = apps.get_model("contabilidad", "DetalleAsiento")
                    PlanContable = apps.get_model("contabilidad", "PlanContable")
                    from apps.finance.models.currencies import Moneda

                    glosa = payload.get("glosa", "Asiento sugerido por IA")
                    detalles = payload.get("detalles", [])

                    with transaction.atomic():
                        moneda_usd = Moneda.objects.filter(codigo_iso="USD").first()

                        import uuid

                        asiento = AsientoContable.objects.create(
                            agencia=agencia,
                            numero_asiento=f"ASI-IA-{uuid.uuid4().hex[:8].upper()}",
                            descripcion_general=glosa,
                            tipo_asiento="DIA",
                            estado="CON",
                            moneda=moneda_usd,
                            tasa_cambio_aplicada=1.0,
                        )

                        codigos = [d.get("codigo_cuenta") for d in detalles]
                        cuentas_map = {
                            c.codigo_cuenta: c
                            for c in PlanContable.objects.filter(
                                codigo_cuenta__in=codigos, agencia=agencia
                            )
                        }
                        for idx, d in enumerate(detalles, start=1):
                            codigo = d.get("codigo_cuenta")
                            cuenta = cuentas_map.get(codigo)

                            debe = Decimal(str(d.get("debe", 0)))
                            haber = Decimal(str(d.get("haber", 0)))

                            DetalleAsiento.objects.create(
                                agencia=agencia,
                                asiento=asiento,
                                linea=idx,
                                cuenta_contable=cuenta,
                                debe=debe,
                                haber=haber,
                                descripcion_linea=glosa,
                            )

                        asiento.calcular_totales(commit=True)

                    execution_msg = f"Se ha creado y contabilizado el asiento contable número {asiento.id_asiento} exitosamente."

                else:
                    return Response(
                        {
                            "error": f"Acción '{propuesta.accion_tipo}' no soportada por el motor de ejecución contable."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Guardar estado aprobado
                propuesta.estado = PropuestaTransaccionIA.EstadoPropuesta.APROBADA
                propuesta.fecha_resolucion = timezone.now()
                propuesta.usuario_resolutor = request.user
                propuesta.comentarios_resolucion = comentarios or "Aprobado y ejecutado por el CFO."
                propuesta.save()

                return Response(
                    {
                        "status": "propuesta_aprobada",
                        "message": f"La propuesta ha sido aprobada y procesada. {execution_msg}",
                    }
                )

            except Exception as e:
                logger.exception("Error al procesar y aprobar propuesta contable de la IA")
                return Response(
                    {"error": f"Error de ejecución: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            return Response(
                {"error": "Acción inválida. Use 'approve' o 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AIAccountingProposalsPartialView(LoginRequiredMixin, View):
    """
    Retorna la lista de propuestas pendientes en formato HTML para HTMX.
    """

    def get(self, request):
        agencia = getattr(request, "agencia", None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            if ua:
                agencia = ua.agencia

        if not agencia:
            return HttpResponse("<div class='text-rose-400 text-xs'>Sin agencia activa</div>")

        propuestas = PropuestaTransaccionIA.objects.filter(
            agencia=agencia, estado=PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE
        ).order_by("-fecha_creacion")

        return render(
            request, "finance/partials/pending_proposals.html", {"propuestas": propuestas}
        )


class AIAccountingResolveProposalHTMXView(LoginRequiredMixin, View):
    """
    Procesa la aprobación o rechazo de una propuesta vía HTMX y retorna la lista actualizada.
    """

    def post(self, request, pk, action):
        agencia = getattr(request, "agencia", None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            if ua:
                agencia = ua.agencia

        if not agencia:
            return HttpResponse(
                "<div class='text-rose-400 text-xs'>Sin agencia activa</div>", status=403
            )

        propuesta = get_object_or_404(PropuestaTransaccionIA, pk=pk, agencia=agencia)

        if propuesta.estado != PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE:
            return HttpResponse(
                "<div class='text-rose-400 text-xs'>Propuesta ya procesada</div>", status=400
            )

        comentarios = request.POST.get("comentarios", "")

        try:
            if action == "reject":
                propuesta.estado = PropuestaTransaccionIA.EstadoPropuesta.RECHAZADA
                propuesta.fecha_resolucion = timezone.now()
                propuesta.usuario_resolutor = request.user
                propuesta.comentarios_resolucion = (
                    comentarios or "Rechazado manualmente por el CFO en panel."
                )
                propuesta.save()
            elif action == "approve":
                payload = propuesta.payload_datos

                # Ejecutar de forma determinista y transaccional
                if propuesta.accion_tipo == "CONCILIAR_REPORTE":
                    report_id = payload.get("report_id")
                    if not report_id:
                        raise ValidationError("El payload no contiene 'report_id'.")

                    from django.db import transaction

                    from apps.finance.tasks_reconciliation import conciliar_reporte_batch_task

                    transaction.on_commit(
                        lambda: conciliar_reporte_batch_task.delay(report_id, agencia.pk)
                    )

                elif propuesta.accion_tipo == "CREAR_ASIENTO":
                    from decimal import Decimal

                    from django.apps import apps
                    from django.db import transaction

                    AsientoContable = apps.get_model("contabilidad", "AsientoContable")
                    DetalleAsiento = apps.get_model("contabilidad", "DetalleAsiento")
                    PlanContable = apps.get_model("contabilidad", "PlanContable")
                    from apps.finance.models.currencies import Moneda

                    glosa = payload.get("glosa", "Asiento sugerido por IA")
                    detalles = payload.get("detalles", [])

                    with transaction.atomic():
                        moneda_usd = Moneda.objects.filter(codigo_iso="USD").first()

                        import uuid

                        asiento = AsientoContable.objects.create(
                            agencia=agencia,
                            numero_asiento=f"ASI-IA-{uuid.uuid4().hex[:8].upper()}",
                            descripcion_general=glosa,
                            tipo_asiento="DIA",
                            estado="CON",
                            moneda=moneda_usd,
                            tasa_cambio_aplicada=1.0,
                        )

                        codigos = [d.get("codigo_cuenta") for d in detalles]
                        cuentas_map = {
                            c.codigo_cuenta: c
                            for c in PlanContable.objects.filter(
                                codigo_cuenta__in=codigos, agencia=agencia
                            )
                        }
                        for idx, d in enumerate(detalles, start=1):
                            codigo = d.get("codigo_cuenta")
                            cuenta = cuentas_map.get(codigo)

                            debe = Decimal(str(d.get("debe", 0)))
                            haber = Decimal(str(d.get("haber", 0)))

                            DetalleAsiento.objects.create(
                                agencia=agencia,
                                asiento=asiento,
                                linea=idx,
                                cuenta_contable=cuenta,
                                debe=debe,
                                haber=haber,
                                descripcion_linea=glosa,
                            )

                        asiento.calcular_totales(commit=True)
                else:
                    return HttpResponse(
                        "<div class='text-rose-400 text-xs'>Acción no soportada</div>", status=400
                    )

                propuesta.estado = PropuestaTransaccionIA.EstadoPropuesta.APROBADA
                propuesta.fecha_resolucion = timezone.now()
                propuesta.usuario_resolutor = request.user
                propuesta.comentarios_resolucion = comentarios or "Aprobado y ejecutado por el CFO."
                propuesta.save()
        except Exception as e:
            logger.exception("Error al procesar propuesta contable de la IA via HTMX")
            return HttpResponse(
                f"<div class='text-rose-400 text-xs'>Error: {str(e)}</div>", status=500
            )

        # Retornar la lista actualizada de propuestas para actualizar el contenedor
        propuestas = PropuestaTransaccionIA.objects.filter(
            agencia=agencia, estado=PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE
        ).order_by("-fecha_creacion")

        response = render(
            request,
            "finance/partials/pending_proposals.html",
            {"propuestas": propuestas, "success_msg": "Propuesta procesada exitosamente."},
        )
        response["HX-Trigger"] = "proposalChanged"
        return response

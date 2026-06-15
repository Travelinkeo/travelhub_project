"""
core/views/upload.py
====================
Vistas para subida, revisión y gestión de boletos importados.

Fase 8 - Síncrono Perfecto (Rebobinado de Stream):
- Se implementó archivo_boleto.seek(0) para solucionar el bug del cursor EOF.
- Garantiza que la IA y Gotenberg puedan leer el PDF en el primer intento.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError, DataError, IntegrityError
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import patch_cache_control

from apps.automation.parsers.normalization import DataNormalizationService
from apps.automation.parsers.ticket_parser import FastDeterministicParsers
from apps.automation.services.ticket_parser_service import TicketParserService
from apps.automation.services.ticket_review_service import StudioFormData, TicketReviewService
from apps.bookings.models import BoletoImportado
from apps.crm.models import Cliente

logger = logging.getLogger(__name__)


class SafeDict(dict):
    """Evita errores 500 en los templates cuando faltan llaves en el JSON."""

    def __getitem__(self, key):
        return super().get(key, "")

    def __getattr__(self, key):
        return super().get(key, "")


@method_decorator(login_required, name="dispatch")
class UploadBoletoView(View):
    def post(self, request, *args, **kwargs):
        archivo = request.FILES.get("archivo")
        if not archivo:
            return HttpResponse(
                '<div class="text-red-400 text-sm">Error: Falta archivo</div>', status=400
            )

        try:
            agencia = getattr(request, "agencia", None)
            if not agencia and request.user.is_authenticated:
                ua = request.user.agencias.filter(activo=True).first()
                if ua:
                    agencia = ua.agencia

            boleto_temp = BoletoImportado(
                archivo_boleto=archivo,
                agencia=agencia,
                estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO,
            )
            boleto_temp._skip_auto_parse = True
            # Aquí Django guarda el archivo y deja el cursor al final (EOF)
            boleto_temp.save()

            # Recargamos el boleto fresco
            boleto = BoletoImportado.objects.get(pk=boleto_temp.pk)

            # 🩹 MONKEY PATCH
            if not hasattr(boleto, "id"):
                boleto.id = boleto.pk

            # ⏪ REBOBINADO DEL ARCHIVO (LA VERDADERA MAGIA)
            # Esto obliga al cursor a volver al Byte 0 para que la IA no lea un archivo "vacío"
            if boleto.archivo_boleto and hasattr(boleto.archivo_boleto, "seek"):
                boleto.archivo_boleto.open()
                boleto.archivo_boleto.seek(0)

            # 🚀 PROCESAMIENTO SÍNCRONO DIRECTO
            # bypass_cache=True: fuerza re-parseo fresco (ignora caché Redis del texto)
            # ignore_manual=True: no reutiliza datos_parseados existentes (siempre corre la IA/Regex)
            logger.info(f"Iniciando parseo síncrono en el 1er intento para boleto {boleto.pk}")
            parser_service = TicketParserService()
            parser_service.procesar_boleto(
                boleto_id=boleto.pk, bypass_cache=True, ignore_manual=True
            )

            # Redirección inmediata con los datos ya procesados. El PDF se generará asíncronamente en segundo plano.
            try:
                from apps.bookings.models import BoletoImportadoTransito

                transitos = BoletoImportadoTransito.objects.filter(boleto_origen=boleto).count()
                if transitos > 1:
                    messages.success(
                        request,
                        f"¡Éxito! Se detectó un grupo de {transitos} pasajeros en el archivo. Estás revisando el primero. Los demás ya se importaron automáticamente.",
                    )
            except Exception as ex_msg:
                logger.warning(f"No se pudo chequear pasajeros múltiples para mensaje: {ex_msg}")

            review_url = reverse("core:revisar_boleto", kwargs={"pk": boleto.pk})
            response = HttpResponse()
            response["HX-Redirect"] = review_url
            return response

        except Exception as e:
            logger.exception(f"Error crítico en subida de boleto: {e}")
            return HttpResponse(
                '<div class="fixed bottom-5 right-5 bg-red-900 border-l-4 border-red-500 text-white p-4 rounded shadow-xl">'
                "Error al procesar la Inteligencia Artificial. Reintente o contacte a soporte.</div>",
                status=500,
            )


@method_decorator(login_required, name="dispatch")
class ReviewBoletoView(View):
    template_name = "core/tickets/review_master.html"

    def get(self, request, pk, *args, **kwargs):
        manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
        boleto = get_object_or_404(manager, pk=pk)

        agencia = getattr(request, "agencia", None)
        if not request.user.is_superuser and boleto.agencia != agencia:
            return HttpResponse("Acceso Denegado", status=403)

        force = request.GET.get("force") == "1"

        if not hasattr(boleto, "id"):
            boleto.id = boleto.pk

        # 🚀 RE EXTRAER SÍNCRONO MANUAL
        if force:
            logger.info(f"🔄 Re-extracción forzada (bypass_cache + ignore_manual) Boleto {pk}")
            boleto.estado_parseo = BoletoImportado.EstadoParseo.EN_PROCESO
            boleto.save(update_fields=["estado_parseo"])

            # Rebobinado por seguridad
            if boleto.archivo_boleto and hasattr(boleto.archivo_boleto, "seek"):
                boleto.archivo_boleto.open()
                boleto.archivo_boleto.seek(0)

            parser_service = TicketParserService()
            parser_service.procesar_boleto(
                boleto_id=boleto.pk, bypass_cache=True, ignore_manual=True
            )

            return redirect("core:revisar_boleto", pk=pk)

        # 🤖 AUTO-RECUPERACIÓN
        estado_str = str(boleto.estado_parseo)
        if estado_str in ["PEN", "PRO", "QUE", "COLA_LLENA", "EN_PROCESO", "PENDIENTE"]:
            debe_procesar = True
            if estado_str in ["PRO", "EN_PROCESO"]:
                import datetime

                from django.utils import timezone

                if boleto.updated_at and (timezone.now() - boleto.updated_at) < datetime.timedelta(
                    seconds=15
                ):
                    logger.info(
                        f"Boleto {pk} está en proceso en background (actualizado hace poco). Omitiendo auto-recuperación por ahora."
                    )
                    debe_procesar = False

            if debe_procesar:
                logger.info(f"Procesando boleto atascado {pk} síncronamente.")

                if boleto.archivo_boleto and hasattr(boleto.archivo_boleto, "seek"):
                    boleto.archivo_boleto.open()
                    boleto.archivo_boleto.seek(0)

                parser_service = TicketParserService()
                parser_service.procesar_boleto(boleto_id=boleto.pk, ignore_manual=True)
                boleto.refresh_from_db()

        try:
            source_text = (
                TicketParserService()._extraer_texto(boleto)
                or boleto.log_parseo
                or "Sin texto fuente."
            )
        except Exception:
            source_text = boleto.log_parseo or "Error al leer el archivo."

        datos_crudos = boleto.datos_parseados or {}
        datos_norm = DataNormalizationService.normalize_ticket_data(datos_crudos)
        datos = SafeDict(datos_norm)

        if not datos.get("pnr"):
            regex_emergency = FastDeterministicParsers.parse_general_regex(source_text)
            if regex_emergency.get("codigo_reserva"):
                datos.update(DataNormalizationService.normalize_ticket_data(regex_emergency))

        segments = datos.get("segmentos", [])

        response = render(
            request,
            self.template_name,
            {
                "boleto": boleto,
                "parsed_data": datos,
                "segments": segments,
                "agencia": agencia,
                "clientes": Cliente.objects.filter(agencia=agencia).order_by("apellidos", "nombres")
                if agencia
                else [],
                "is_processing": False,
                "error_ia": datos.get("error_ia"),
                "source_text": source_text,
                "csp_nonce": getattr(request, "csp_nonce", ""),
            },
        )
        patch_cache_control(response, no_cache=True, no_store=True, must_revalidate=True, max_age=0)
        return response

    def post(self, request, pk, *args, **kwargs):
        try:
            next_url = request.GET.get("next") or request.POST.get("next")
            manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
            boleto = manager.get(pk=pk)

            agencia = getattr(request, "agencia", None)
            if not request.user.is_superuser and boleto.agencia != agencia:
                return HttpResponse("Acceso Denegado", status=403)

            if not hasattr(boleto, "id"):
                boleto.id = boleto.pk

            form_data = StudioFormData.from_post(request.POST)
            resultado = TicketReviewService().apply_and_reprocess(
                boleto=boleto,
                form_data=form_data,
                session=request.session,
            )

            if resultado.success and resultado.venta:
                edit_url = reverse("core:editar_venta", kwargs={"pk": resultado.venta.pk})
                if next_url:
                    edit_url += f"?next={next_url}"
                response = HttpResponse()
                response["HX-Redirect"] = edit_url
                return response

            return HttpResponse(
                f'<div class="bg-red-900 p-4 text-white">Error: {resultado.error_message}</div>',
                status=200,
            )

        except (ValidationError, IntegrityError, DataError, DatabaseError):
            logger.exception("Error de BD en reparse de boleto %s", boleto.pk)
            return HttpResponse(
                '<div class="bg-red-900 p-4 text-white">Error de base de datos al reprocesar. Notifique a soporte.</div>',
                status=500,
            )
        except Exception as e:
            logger.critical(
                "Error inesperado en reparse de boleto %s: %s", boleto.pk, e, exc_info=True
            )
            return HttpResponse(
                '<div class="bg-red-900 p-4 text-white">Error interno inesperado. Contacte a soporte.</div>',
                status=500,
            )


@method_decorator(login_required, name="dispatch")
class BoletoStatusView(View):
    def get(self, request, pk, *args, **kwargs):
        return HttpResponse("<script>window.location.reload();</script>")


@method_decorator(login_required, name="dispatch")
class BoletoPdfStatusView(View):
    MAX_POLLS = 30  # ~2 minutos (30 * 4s)

    def get(self, request, pk, *args, **kwargs):
        manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
        boleto = get_object_or_404(manager, pk=pk)

        agencia = getattr(request, "agencia", None)
        if not request.user.is_superuser and boleto.agencia != agencia:
            return HttpResponse("Acceso Denegado", status=403)

        poll_count = int(request.GET.get("poll", "0"))
        if poll_count > self.MAX_POLLS:
            return HttpResponse(f"""
            <div id="pdf-status-container-{boleto.pk}" class="flex-1 h-10 px-4 rounded-xl bg-red-500/5 border border-red-500/20 flex items-center justify-center gap-2 text-red-500 group" title="Tiempo de espera agotado. Recarga la página.">
                <span class="material-symbols-outlined text-[16px]">timer_off</span>
                <span class="text-[9px] font-black uppercase tracking-wider">Tiempo agotado — Recarga</span>
            </div>
            """)

        # Si el boleto lleva demasiado tiempo en PRO, expirar el estado
        if boleto.estado_parseo == BoletoImportado.EstadoParseo.EN_PROCESO:
            from django.utils import timezone as tz
            if boleto.updated_at and (tz.now() - boleto.updated_at).total_seconds() > 120:
                BoletoImportado.all_objects.filter(pk=boleto.pk).update(
                    estado_parseo="REV",
                    log_parseo="Estado PRO expirado por timeout (>120s). Reintenta el parseo."
                )
                boleto.refresh_from_db()

        retry = request.GET.get("retry") == "1"
        if retry:
            try:
                # FIX: Generación síncrona — no depende de Celery ni Redis.
                # Antes se encolaba en Celery y podía tardar horas si el worker estaba ocupado.
                # Ahora se genera directamente con WeasyPrint en este mismo request (~1-5s).
                from apps.automation.services.ticket_parser_service import _generate_pdf_sync

                logger.info(f"🔄 Re-generando PDF síncronamente para Boleto {boleto.pk}")

                # Limpiar PDF corrupto o vacío previo para forzar regeneración
                if boleto.archivo_pdf_generado:
                    try:
                        boleto.archivo_pdf_generado.delete(save=False)
                    except Exception:
                        pass
                    boleto.archivo_pdf_generado = None
                    boleto.save(update_fields=["archivo_pdf_generado"])

                # Regenerar de inmediato — mismo mecanismo que usa el pipeline internamente
                boleto.refresh_from_db()
                _generate_pdf_sync(boleto)
                logger.info(f"✅ PDF re-generado síncronamente para Boleto {boleto.pk}")
            except Exception as e_pdf_queue:
                logger.error(f"❌ Error al re-generar PDF síncronamente: {e_pdf_queue}")

        if boleto.archivo_pdf_generado:
            # Verificar que el archivo exista físicamente (FileSystemStorage) o en R2
            pdf_accessible = False
            try:
                pdf_accessible = boleto.archivo_pdf_generado.storage.exists(
                    boleto.archivo_pdf_generado.name
                )
            except Exception:
                # En R2/S3, asumimos que existe si hay nombre
                pdf_accessible = bool(boleto.archivo_pdf_generado.name)

            if pdf_accessible:
                html = f"""
                <a href="{boleto.archivo_pdf_generado.url}" target="_blank" class="flex-1 h-10 px-4 rounded-xl bg-status-success-bg border border-status-success/20 flex items-center justify-center gap-2 hover:bg-status-success-bg/80 transition-all text-status-success group">
                    <span class="material-symbols-outlined text-[16px]">verified</span>
                    <span class="text-[9px] font-black uppercase tracking-wider">TKT</span>
                </a>
                """
                return HttpResponse(html)
            else:
                # Archivo registrado pero no encontrado en disco — regenerar síncronamente
                logger.warning(
                    f"⚠️ PDF registrado pero no encontrado para Boleto {boleto.pk}. Regenerando..."
                )
                try:
                    from apps.automation.services.ticket_parser_service import _generate_pdf_sync

                    boleto.archivo_pdf_generado = None
                    boleto.save(update_fields=["archivo_pdf_generado"])
                    boleto.refresh_from_db()
                    _generate_pdf_sync(boleto)
                    boleto.refresh_from_db()
                except Exception as e_regen:
                    logger.error(
                        f"❌ Error regenerando PDF perdido para Boleto {boleto.pk}: {e_regen}"
                    )
                # Si ahora existe, mostrar; si no, caer al estado de "Generando..."
                if boleto.archivo_pdf_generado:
                    html = f"""
                    <a href="{boleto.archivo_pdf_generado.url}" target="_blank" class="flex-1 h-10 px-4 rounded-xl bg-status-success-bg border border-status-success/20 flex items-center justify-center gap-2 hover:bg-status-success-bg/80 transition-all text-status-success group">
                        <span class="material-symbols-outlined text-[16px]">verified</span>
                        <span class="text-[9px] font-black uppercase tracking-wider">TKT</span>
                    </a>
                    """
                    return HttpResponse(html)

        if boleto.estado_parseo == BoletoImportado.EstadoParseo.ERROR_PARSEO:
            url = reverse("core:boleto_pdf_status", kwargs={"pk": boleto.pk}) + "?retry=1&poll=0"
            html = f"""
            <div id="pdf-status-container-{boleto.pk}" 
                 hx-get="{url}" 
                 hx-trigger="click" 
                 hx-swap="outerHTML" 
                 class="flex-1 h-10 px-4 rounded-xl bg-red-500/5 border border-red-500/20 flex items-center justify-center gap-2 text-red-500 group cursor-pointer"
                 title="Error al generar PDF. Clic para reintentar.">
                <span class="material-symbols-outlined text-[16px]">error</span>
                <span class="text-[9px] font-black uppercase tracking-wider">Error TKT — Clic para reintentar</span>
            </div>
            """
            return HttpResponse(html)

        # Boleto ya completó parseo (COM/REV) pero no tiene PDF → regenerar síncronamente ahora
        # Esto evita que la UI quede en bucle infinito de "Generando..."
        estado_final = str(boleto.estado_parseo)
        if estado_final in ("COM", "REV", "COMPLETADO", "REVISION_REQUERIDA"):
            logger.info(
                f"⚡ [PDF-STATUS] Boleto {boleto.pk} completó parseo ({estado_final}) pero no tiene PDF. "
                "Regenerando síncronamente..."
            )
            try:
                from apps.automation.services.ticket_parser_service import _generate_pdf_sync

                _generate_pdf_sync(boleto)
                boleto.refresh_from_db()
            except Exception as e_regen:
                logger.error(f"❌ [PDF-STATUS] Fallo al auto-regenerar PDF para Boleto {boleto.pk}: {e_regen}")

            # Si ahora tenemos PDF, mostrarlo
            if boleto.archivo_pdf_generado:
                try:
                    pdf_accessible = boleto.archivo_pdf_generado.storage.exists(
                        boleto.archivo_pdf_generado.name
                    )
                except Exception:
                    pdf_accessible = bool(boleto.archivo_pdf_generado.name)

                if pdf_accessible:
                    html = f"""
                    <a href="{boleto.archivo_pdf_generado.url}" target="_blank" class="flex-1 h-10 px-4 rounded-xl bg-status-success-bg border border-status-success/20 flex items-center justify-center gap-2 hover:bg-status-success-bg/80 transition-all text-status-success group">
                        <span class="material-symbols-outlined text-[16px]">verified</span>
                        <span class="text-[9px] font-black uppercase tracking-wider">TKT</span>
                    </a>
                    """
                    return HttpResponse(html)

            # Si sigue sin PDF después del intento, mostrar botón de error (sale del bucle)
            boleto.refresh_from_db()
            url_retry = reverse("core:boleto_pdf_status", kwargs={"pk": boleto.pk}) + "?retry=1&poll=0"
            html = f"""
            <div id="pdf-status-container-{boleto.pk}" 
                 hx-get="{url_retry}" 
                 hx-trigger="click" 
                 hx-swap="outerHTML" 
                 class="flex-1 h-10 px-4 rounded-xl bg-red-500/5 border border-red-500/20 flex items-center justify-center gap-2 text-red-500 group cursor-pointer"
                 title="Error al generar PDF. Clic para reintentar.">
                <span class="material-symbols-outlined text-[16px]">error</span>
                <span class="text-[9px] font-black uppercase tracking-wider">Error TKT — Clic para reintentar</span>
            </div>
            """
            return HttpResponse(html)

        # Aún en proceso (PRO/EN_PROCESO) — seguir esperando con polling limitado
        # El contador hx-vals evita polling eterno si el backend no responde
        next_poll = poll_count + 1
        url = reverse("core:boleto_pdf_status", kwargs={"pk": boleto.pk})
        html = f"""
        <div id="pdf-status-container-{boleto.pk}" 
             hx-get="{url}?poll={next_poll}" 
             hx-trigger="every 4s" 
             hx-swap="outerHTML" 
             class="flex-1 h-10 px-4 rounded-xl bg-amber-500/5 border border-amber-500/20 flex items-center justify-center gap-2 text-amber-500 group animate-pulse cursor-wait">
            <span class="size-4 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin"></span>
            <span class="text-[9px] font-black uppercase tracking-wider">Generando...</span>
        </div>
        """
        return HttpResponse(html)


@method_decorator(login_required, name="dispatch")
class DesasociarVentaView(View):
    def post(self, request, pk):
        boleto = get_object_or_404(BoletoImportado, pk=pk)
        agencia = getattr(request, "agencia", None)
        if not request.user.is_superuser and boleto.agencia != agencia:
            return HttpResponse("Acceso Denegado", status=403)

        if boleto.venta_asociada:
            boleto.venta_asociada = None
            boleto.estado_parseo = "REV"  # REVISION_REQUERIDA (max_length=3)
            boleto.save()
            messages.info(request, "Boleto desasociado de la venta.")

        return redirect("core:revisar_boleto", pk=pk)


@login_required
def eliminar_boleto(request, pk):
    manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
    boleto = get_object_or_404(manager, pk=pk)

    if not request.user.is_superuser and hasattr(request, "agencia"):
        if boleto.agencia != request.agencia:
            messages.error(request, "Acceso Denegado.")
            return redirect("core:boletos_importar")
    try:
        try:
            if boleto.archivo_boleto:
                boleto.archivo_boleto.delete(save=False)
        except Exception:
            pass
        try:
            if getattr(boleto, "archivo_pdf_generado", None):
                boleto.archivo_pdf_generado.delete(save=False)
        except Exception:
            pass
        boleto.hard_delete()
        messages.success(request, "Boleto eliminado físicamente.")
    except ProtectedError:
        logger.exception("Intento de eliminar boleto %s con referencias protegidas", pk)
        messages.error(request, "No se puede eliminar: el boleto tiene registros asociados.")
    except (OSError, DatabaseError):
        logger.exception("Error de almacenamiento/BD al eliminar boleto %s", pk)
        messages.error(request, "Error al eliminar archivos o base de datos. Contacte a soporte.")
    except Exception as e:
        logger.critical("Error inesperado eliminando boleto %s: %s", pk, e, exc_info=True)
        messages.error(request, "Error interno inesperado. Contacte a soporte.")

    return redirect(request.GET.get("next") or "core:boletos_importar")

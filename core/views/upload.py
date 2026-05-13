"""
core/views/upload.py
====================
Vistas para subida, revisión y gestión de boletos importados.

Fase 2 - Refactorización:
- Todos los imports movidos al nivel del módulo (elimina E402 y dependencias ocultas).
- Import roto de celery_utils corregido (apps.common.utils → era ..utils).
- Logging centralizado vía logger del módulo.
"""
import logging
import traceback

from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
from apps.common.utils.celery_utils import safe_delay
from apps.crm.models import Cliente
from core.tasks import parsear_boleto_individual

logger = logging.getLogger(__name__)


class SafeDict(dict):
    """
    Evita errores 500 de VariableDoesNotExist en los templates de Django
    cuando faltan llaves en el JSON de la IA.
    """
    def __getitem__(self, key):
        return super().get(key, '')

    def __getattr__(self, key):
        return super().get(key, '')


@method_decorator(login_required, name='dispatch')
class UploadBoletoView(View):
    def post(self, request, *args, **kwargs):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return HttpResponse('<div class="text-red-400 text-sm">Error: Falta archivo</div>', status=400)

        try:
            # 1. Guardar el boleto inicial
            agencia = getattr(request, 'agencia', None)
            if not agencia and request.user.is_authenticated:
                ua = request.user.agencias.filter(activo=True).first()
                if ua:
                    agencia = ua.agencia

            boleto = BoletoImportado.objects.create(
                archivo_boleto=archivo,
                agencia=agencia,
                estado_parseo='PEN'
            )

            # 2. Procesamiento Asíncrono (Celery)
            safe_delay(parsear_boleto_individual, boleto.pk)

            # Redirigir INMEDIATAMENTE al Review Master
            review_url = reverse('core:revisar_boleto', kwargs={'pk': boleto.pk})
            response = HttpResponse()
            response['HX-Redirect'] = review_url
            return response

        except Exception as e:
            logger.exception(f"Error en subida de boleto: {e}")
            return HttpResponse(
                f'<div class="fixed bottom-5 right-5 bg-red-900 border-l-4 border-red-500 text-white p-4 rounded shadow-xl animate-bounce-in">'
                f'Error al recibir boleto: {str(e)}</div>',
                status=200
            )


@method_decorator(login_required, name='dispatch')
class ReviewBoletoView(View):
    template_name = 'core/tickets/review_master.html'

    def get(self, request, pk, *args, **kwargs):
        try:
            boleto = BoletoImportado.all_objects.get(pk=pk)
        except BoletoImportado.DoesNotExist:
            return HttpResponse("Boleto no encontrado", status=404)

        # Seguridad multi-tenant
        agencia = getattr(request, 'agencia', None)
        if not request.user.is_superuser and boleto.agencia != agencia:
            return HttpResponse("No tiene permisos para ver este boleto", status=403)

        next_url = request.GET.get('next')

        # --- LÓGICA DE RE-PARSEO (ASYNC) ---
        force = request.GET.get('force') == '1'
        # Detectamos si ya está en un estado activo de procesamiento para no duplicar tareas
        is_processing = boleto.estado_parseo in [BoletoImportado.EstadoParseo.EN_PROCESO, BoletoImportado.EstadoParseo.COLA_LLENA]

        # Detector de Tareas Atascadas (Self-Healing)
        # Si lleva más de 5 minutos en PRO, permitimos re-intentar
        from django.utils import timezone
        import datetime
        
        time_since_update = timezone.now() - (getattr(boleto, 'updated_at', None) or boleto.fecha_subida)
        is_stuck = is_processing and time_since_update > datetime.timedelta(minutes=5)
        
        if force or is_stuck:
            logger.info(f"🔄 Acción de Recuperación para Boleto {pk} (Force={force}, Stuck={is_stuck})")
            if is_stuck:
                # Si está atascado, marcamos como ERROR y re-encolamos con ignore_manual
                logger.error(f"🚨 Tarea atascada detectada en Boleto {pk}. Re-encolando...")
                boleto.estado_parseo = BoletoImportado.EstadoParseo.COLA_LLENA
                boleto.log_parseo = f"{boleto.log_parseo or ''}\n[TIMEOUT] Tarea atascada detectada ({time_since_update.seconds}s). Re-encolando procesamiento."
                is_processing = True
                safe_delay(parsear_boleto_individual, boleto.pk, ignore_manual=True, bypass_cache=True)
            else:
                # Force manual
                boleto.estado_parseo = BoletoImportado.EstadoParseo.COLA_LLENA
                boleto.log_parseo = "Re-procesamiento solicitado manualmente."
                safe_delay(parsear_boleto_individual, boleto.pk, ignore_manual=True, bypass_cache=True)
                is_processing = True
            
            boleto.save(update_fields=['estado_parseo', 'log_parseo'])

        # Solo auto-reintentar si está Pendiente (PEN) y es realmente necesario
        if not is_processing and boleto.estado_parseo == BoletoImportado.EstadoParseo.PENDIENTE:
            needs_parsing = not boleto.datos_parseados or \
                           (isinstance(boleto.datos_parseados, dict) and not boleto.datos_parseados.get('passenger_name'))
            
            if needs_parsing:
                logger.info(f"🤖 Auto-triggering parsing for new ticket {pk}")
                boleto.estado_parseo = BoletoImportado.EstadoParseo.COLA_LLENA
                boleto.save(update_fields=['estado_parseo'])
                # Usamos safe_delay para encolar en Celery
                safe_delay(parsear_boleto_individual, boleto.pk)
                is_processing = True

        # Asegurar que el texto original esté disponible para el panel de "Fuente"
        try:
            source_text = (
                TicketParserService()._extraer_texto(boleto)
                or boleto.log_parseo
                or "No se pudo extraer texto del archivo."
            )
        except Exception as e:
            logger.warning(f"Error extrayendo texto fuente del boleto {pk}: {e}")
            source_text = boleto.log_parseo or "Error al leer el archivo fuente."

        # --- NORMALIZACIÓN DE DATOS PARA EL UI (Studio) ---
        datos_crudos = boleto.datos_parseados or {}
        datos_norm = DataNormalizationService.normalize_ticket_data(datos_crudos)
        datos = SafeDict(datos_norm)

        if not datos.get('pnr') and not is_processing:
            regex_emergency = FastDeterministicParsers.parse_general_regex(source_text)
            if regex_emergency.get('codigo_reserva'):
                datos.update(DataNormalizationService.normalize_ticket_data(regex_emergency))

        segments = boleto.datos_parseados.get('segmentos', []) if boleto.datos_parseados else []

        response = render(request, self.template_name, {
            'boleto': boleto,
            'parsed_data': datos,
            'segments': segments,
            'agencia': agencia,
            'clientes': Cliente.objects.filter(agencia=agencia).order_by('apellidos', 'nombres') if agencia else [],
            'is_processing': is_processing,
            'error_ia': datos.get('error_ia'),
            'source_text': source_text,
            'next_url': next_url,
            'csp_nonce': getattr(request, 'csp_nonce', ''),
        })

        # 🛡️ ANTI-CACHE GLOBAL (Browser, Cloudflare, Nginx)
        patch_cache_control(response, no_cache=True, no_store=True, must_revalidate=True, max_age=0)
        return response

    def post(self, request, pk, *args, **kwargs):
        try:
            next_url = request.GET.get('next') or request.POST.get('next')
            boleto = BoletoImportado.all_objects.get(pk=pk)

            # Seguridad multi-tenant
            agencia = getattr(request, 'agencia', None)
            if not request.user.is_superuser and boleto.agencia != agencia:
                return HttpResponse("No tiene permisos para modificar este boleto", status=403)

            # Parsear formulario y delegar toda la lógica de negocio al servicio
            form_data = StudioFormData.from_post(request.POST)
            resultado = TicketReviewService().apply_and_reprocess(
                boleto=boleto,
                form_data=form_data,
                session=request.session,
            )

            if resultado.success and resultado.venta:
                edit_url = reverse('core:editar_venta', kwargs={'pk': resultado.venta.pk})
                if next_url:
                    edit_url += f"?next={next_url}"
                response = HttpResponse()
                response['HX-Redirect'] = edit_url
                return response

            error_msg = resultado.error_message or "Error desconocido al reprocesar."
            return HttpResponse(
                f'<div class="bg-red-900/50 p-4 rounded-xl border border-red-500/30 text-white font-bold">'
                f'Error: {error_msg}</div>',
                status=200
            )

        except Exception as e:
            logger.error(f"Error en ReviewBoletoView: {e}\n{traceback.format_exc()}")
            return HttpResponse(
                f'<div class="bg-red-900/50 p-4 rounded-xl border border-red-500/30 text-white font-bold">'
                f'Error crítico: {str(e)}</div>',
                status=200
            )


@method_decorator(login_required, name='dispatch')
class DesasociarVentaView(View):
    """
    Desasocia un boleto de su venta actual para permitir un re-parseo limpio.
    """
    def post(self, request, pk):
        boleto = get_object_or_404(BoletoImportado, pk=pk)

        # Seguridad multi-tenant
        agencia = getattr(request, 'agencia', None)
        if not request.user.is_superuser and boleto.agencia != agencia:
            return HttpResponse("No tiene permisos para desasociar este boleto", status=403)

        if boleto.venta_asociada:
            venta = boleto.venta_asociada
            boleto.venta_asociada = None
            boleto.estado_parseo = 'PEN'
            boleto.save()
            messages.info(
                request,
                f"Boleto desasociado de la venta {venta.localizador}. El boleto está listo para re-procesarse."
            )

        return redirect('core:revisar_boleto', pk=pk)


@login_required
def eliminar_boleto(request, pk):
    """🗑️ Eliminación física de un boleto y sus archivos."""
    boleto = get_object_or_404(BoletoImportado.all_objects, pk=pk)

    # Seguridad: Solo la misma agencia
    if not request.user.is_superuser and hasattr(request, 'agencia'):
        if boleto.agencia != request.agencia:
            messages.error(request, "No tiene permisos para eliminar este boleto.")
            return redirect('core:boletos_importar')

    try:
        if boleto.archivo_boleto:
            boleto.archivo_boleto.delete(save=False)
        if boleto.archivo_pdf_generado:
            try:
                boleto.archivo_pdf_generado.delete(save=False)
            except Exception as e:
                logger.warning(f"Error eliminando PDF generado del boleto {pk}: {e}")

        boleto.delete(force=True)
        messages.success(request, "Boleto eliminado físicamente con éxito.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {str(e)}")

    return redirect(request.GET.get('next') or 'core:boletos_importar')
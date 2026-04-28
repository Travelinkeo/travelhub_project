# -*- coding: utf-8 -*-
# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE (REFACTORED)
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------
import logging
import time
import traceback
from django.db import transaction, OperationalError
from core.models import Agencia
from apps.bookings.models import BoletoImportado
from core.ticket_parser import extract_data_from_text

# SUB-SERVICES
from core.services.parsers.extraction import ExtractionService
from core.services.parsers.normalization import DataNormalizationService
from core.services.parsers.persistence import BoletoPersistenceService
from core.services.parsers.pdf_generation import PdfGenerationService
from core.services.venta_automation import VentaAutomationService

logger = logging.getLogger(__name__)

class TicketParserService:
    """
    🏢 MULTI-TENANT | 🧠 ORQUESTADOR | 🚨 CRÍTICO
    Punto de entrada unificado para el procesamiento de boletos.
    Coordina la extracción, normalización, persistencia y automatización financiera.
    """

    def procesar_boleto(self, boleto_id, forced_client_id=None, ignore_manual=False):
        """Pipeline principal con lógica de reintentos para evitar deadlocks."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                return self._run_pipeline(boleto_id, forced_client_id, ignore_manual)
            except OperationalError as e:
                if any(err in str(e).lower() for err in ["deadlock", "database is locked"]):
                    if attempt < max_retries - 1:
                        logger.warning(f"🔄 Reintentando por bloqueo de DB ({attempt+1}/{max_retries})...")
                        time.sleep(retry_delay)
                        continue
                raise
            except Exception as e:
                logger.exception(f"❌ Fallo crítico en pipeline para boleto {boleto_id}: {e}")
                raise

    def _run_pipeline(self, boleto_id, forced_client_id, ignore_manual):
        # 0. Carga de instancia
        boleto = BoletoImportado.all_objects.get(pk=boleto_id)
        boleto.log_parseo = "Iniciando pipeline refactorizado..."
        boleto.save(update_fields=['log_parseo'])

        # 1. Extracción de Texto
        raw_file = ExtractionService.get_open_file(boleto)
        texto = ExtractionService.extract_text(raw_file, boleto.archivo_boleto.name)
        
        if not texto:
            return self._finalize_error(boleto, "Archivo vacío o ilegible.")

        # 2. Parsing (Regex/Legacy)
        path_pdf = None
        try: path_pdf = boleto.archivo_boleto.path
        except: pass
        
        try:
            datos = extract_data_from_text(texto, pdf_path=path_pdf)
        except Exception as e:
            logger.error(f"Parser primario falló: {e}")
            datos = {"error": str(e)}

        # Fallback IA
        if not datos or "error" in datos:
            try:
                from core.parsers.ai_universal_parser import UniversalAIParser
                datos = UniversalAIParser().parse(texto, pdf_path=path_pdf)
            except Exception as e_ai:
                return self._finalize_error(boleto, f"Fallo total (Regex + IA): {e_ai}")

        # 3. Normalización
        datos_norm = DataNormalizationService.normalize_ticket_data(datos)

        # 4. Procesamiento Individual (o Múltiple)
        # Por ahora manejamos el caso base (1 ticket por archivo)
        # TODO: Implementar split para multi-pax si el parser devuelve lista
        return self._process_single_ticket(boleto, datos_norm, forced_client_id)

    def _process_single_ticket(self, boleto, data, forced_client_id):
        try:
            with transaction.atomic():
                # A. Persistencia de datos del boleto
                BoletoPersistenceService.update_boleto_from_data(boleto, data)
                BoletoPersistenceService.handle_versioning(boleto)

                # B. Automatización de Venta
                venta = VentaAutomationService.crear_venta_desde_parser(
                    parsed_data=data,
                    agencia=boleto.agencia,
                    usuario=None # Detectado por middleware
                )

                # C. Generación de PDF Unificado
                try:
                    PdfGenerationService.generate_ticket(data, agencia_obj=boleto.agencia, boleto_obj=boleto)
                except Exception as e_pdf:
                    logger.error(f"Fallo generando PDF: {e_pdf}")

                # D. Finalización Exitosa
                boleto.estado_parseo = 'COM'
                boleto.log_parseo = f"Completado exitosamente. Venta ID: {venta.pk if venta else 'N/A'}"
                boleto.save()

                # Notificación (Opcional/Async)
                self._notify_success(venta)

                return venta

        except Exception as e:
            return self._finalize_error(boleto, f"Error en persistencia/venta: {e}")

    def _finalize_error(self, boleto, error_msg):
        logger.error(f"❌ Error Boleto {boleto.pk}: {error_msg}")
        boleto.estado_parseo = 'ERR'
        boleto.log_parseo = error_msg
        boleto.save()
        return None

    def _notify_success(self, venta):
        if not venta: return
        try:
            from core.models.notificaciones import NotificacionAgente
            if hasattr(venta, 'creado_por') and venta.creado_por:
                NotificacionAgente.objects.create(
                    usuario=venta.creado_por,
                    tipo='ai_magic',
                    titulo='Procesamiento Exitoso ✨',
                    mensaje=f"PNR {venta.localizador} integrado correctamente.",
                    icono='auto_awesome'
                )
        except: pass
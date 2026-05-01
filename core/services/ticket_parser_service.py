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

    def procesar_boleto(self, boleto_id, forced_client_id=None, ignore_manual=False, bypass_cache=False, manual_only=False):
        """Pipeline principal con lógica de reintentos para evitar deadlocks."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                return self._run_pipeline(boleto_id, forced_client_id, ignore_manual, bypass_cache, manual_only)
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

    def _run_pipeline(self, boleto_id, forced_client_id, ignore_manual, bypass_cache=False, manual_only=False):
        # 0. Carga de instancia
        boleto = BoletoImportado.all_objects.get(pk=boleto_id)
        
        # 🛡️ MODO MANUAL (Review Master Finalization): 
        # Si el usuario ya revisó y editó, NO corremos nada de extracción. Vamos directo a persistencia y venta.
        if manual_only:
            logger.info(f"💾 Guardando cambios manuales para Boleto {boleto_id} (Finalización Directa)")
            
            # 🛡️ FIX: Asegurar que los datos sean un diccionario (evitar 'str' object has no attribute 'get')
            import json
            datos_para_procesar = boleto.datos_parseados or {}
            if isinstance(datos_para_procesar, str):
                try: datos_para_procesar = json.loads(datos_para_procesar)
                except: datos_para_procesar = {}
                
            datos_norm = DataNormalizationService.normalize_ticket_data(datos_para_procesar)
            return self._process_single_ticket(boleto, datos_norm, forced_client_id)

        # 🧠 INTELIGENCIA DE REUTILIZACIÓN: Si ya tenemos datos y no se forzó el re-parseo, los usamos.
        if not ignore_manual and boleto.datos_parseados and isinstance(boleto.datos_parseados, dict):
            has_basics = boleto.datos_parseados.get('pnr') or boleto.datos_parseados.get('passenger_name')
            if has_basics:
                logger.info(f"♻️ Reutilizando datos existentes para Boleto {boleto_id} (Studio Mode)")
                datos_norm = DataNormalizationService.normalize_ticket_data(boleto.datos_parseados)
                return self._process_single_ticket(boleto, datos_norm, forced_client_id)

        # 1. Adquisición de Lock Atómico
        # Evitamos que dos procesos (Signal vs View vs Celery) procesen lo mismo simultáneamente.
        updated_count = BoletoImportado.objects.filter(
            pk=boleto_id
        ).exclude(
            estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO
        ).update(estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO)

        if updated_count == 0:
            logger.info(f"⏭️ Boleto {boleto_id} ya está siendo procesado por otro hilo. Esperando...")
            # Si ya está en proceso, esperamos unos segundos para ver si termina
            # Esto ayuda a que las vistas síncronas no muestren datos vacíos
            for _ in range(5):
                time.sleep(1)
                boleto.refresh_from_db()
                if boleto.estado_parseo != BoletoImportado.EstadoParseo.EN_PROCESO:
                    break
            return boleto.venta_asociada or True

        boleto.log_parseo = "Iniciando pipeline de extracción..."
        boleto.save(update_fields=['log_parseo'])

        # 2. Extracción de Texto
        raw_file = ExtractionService.get_open_file(boleto)
        texto = ExtractionService.extract_text(raw_file, boleto.archivo_boleto.name)
        
        if not texto:
            return self._finalize_error(boleto, "Archivo vacío o ilegible.")

        # 3. Parsing (Regex/Legacy)
        path_pdf = None
        try: path_pdf = boleto.archivo_boleto.path
        except: pass
        
        datos = None
        try:
            datos_regex = extract_data_from_text(texto, pdf_path=path_pdf, bypass_cache=bypass_cache)
            datos = datos_regex
        except Exception as e:
            logger.error(f"Parser primario falló: {e}")
            datos_regex = None

        # Fallback IA (Solo si Regex falló o si se forzó IA)
        if not datos or "error" in datos or ignore_manual:
            try:
                from core.parsers.ai_universal_parser import UniversalAIParser
                from core.services.ai_engine import QuotaExhaustedException
                
                logger.info(f"🧠 Intentando IA para Boleto {boleto_id}... (Bypass Cache: {bypass_cache})")
                datos_ia = UniversalAIParser().parse(texto, pdf_path=path_pdf, bypass_cache=bypass_cache)
                if datos_ia and "error" not in datos_ia:
                    datos = datos_ia
            except QuotaExhaustedException as eq:
                logger.warning(f"⚠️ IA Agotada (429).")
                if datos_regex:
                    datos = datos_regex
                else:
                    return self._finalize_error(boleto, "IA agotada y el motor tradicional no pudo leer el archivo.")
            except Exception as e_ai:
                logger.error(f"Fallo IA: {e_ai}")
                if not datos_regex:
                    return self._finalize_error(boleto, f"Fallo total (Regex + IA): {e_ai}")

        # 3. Normalización y Procesamiento (Multi-Pax Aware)
        if isinstance(datos, dict) and datos.get('is_multi_pax'):
            tickets = datos.get('tickets', [])
            logger.info(f"👨‍👩‍👧‍👦 Grupo detectado: {len(tickets)} pasajeros. Iniciando Split...")
            
            # El primer boleto usa la instancia actual
            first_ticket_data = DataNormalizationService.normalize_ticket_data(tickets[0])
            venta_maestra = self._process_single_ticket(boleto, first_ticket_data, forced_client_id)
            
            # Los siguientes crean nuevas instancias
            for i, ticket_data in enumerate(tickets[1:], start=1):
                try:
                    logger.info(f"👤 Creando instancia para pasajero adicional {i+1}...")
                    nuevo_boleto = BoletoImportado.objects.create(
                        archivo_boleto=boleto.archivo_boleto,
                        agencia=boleto.agencia,
                        creado_por=boleto.creado_por,
                        estado_parseo='PEN'
                    )
                    norm_data = DataNormalizationService.normalize_ticket_data(ticket_data)
                    # El sistema de automatización de ventas ya sabe unir al PNR existente
                    self._process_single_ticket(nuevo_boleto, norm_data, forced_client_id)
                except Exception as e_multi:
                    logger.error(f"Error procesando pasajero {i+1} del grupo: {e_multi}")
            
            return venta_maestra

        # Procesamiento estándar (Single Pax)
        datos_norm = DataNormalizationService.normalize_ticket_data(datos)
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
                    usuario=None,
                    forced_cliente_id=forced_client_id
                )

                # C. Generación de PDF (Golden Ticket v2)
                try:
                    logger.info(f"📄 Generando TKT PDF para Boleto {boleto.pk}")
                    pdf_bytes, fname = PdfGenerationService.generate_ticket(data, agencia_obj=boleto.agencia, boleto_obj=boleto)
                    
                    if pdf_bytes:
                        from django.core.files.base import ContentFile
                        # Guardamos el archivo físico en el modelo
                        boleto.archivo_pdf_generado.save(fname, ContentFile(pdf_bytes), save=False)
                        logger.info(f"✅ PDF guardado: {fname}")
                    else:
                        logger.warning(f"⚠️ No se generaron bytes para el PDF del Boleto {boleto.pk}")
                except Exception as e_pdf:
                    logger.error(f"❌ Error guardando PDF: {e_pdf}", exc_info=True)

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

    def _extraer_texto(self, boleto):
        """Bridge for legacy code (ReviewBoletoView)"""
        return ExtractionService.extract_text(
            ExtractionService.get_open_file(boleto), 
            boleto.archivo_boleto.name
        )


# -----------------------------------------------------
# 🏛️ LEGACY COMPATIBILITY LAYER
# -----------------------------------------------------
def orquestar_parseo_de_boleto(boleto_id, forced_client_id=None, ignore_manual=False):
    """Bridge for legacy code (views_legacy.py, etc.)"""
    return TicketParserService().procesar_boleto(boleto_id, forced_client_id, ignore_manual)

# Mock para compatibilidad
def generar_pdf_en_memoria(data, agencia_obj=None, boleto_obj=None):
    from core.services.parsers.pdf_generation import PdfGenerationService
    return PdfGenerationService.generate_ticket(data, agencia_obj, boleto_obj)
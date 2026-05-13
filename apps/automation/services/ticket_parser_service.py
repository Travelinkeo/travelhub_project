# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE (REFACTORED)
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------
import hashlib
import logging
import time

from django.core.cache import cache
from django.db import OperationalError, transaction

# SUB-SERVICES
from apps.automation.parsers.extraction import ExtractionService
from apps.automation.parsers.normalization import DataNormalizationService
from apps.automation.parsers.pdf_generation import PdfGenerationService
from apps.automation.parsers.persistence import BoletoPersistenceService
from apps.automation.parsers.ticket_parser import extract_data_from_text
from apps.automation.services.venta_automation import VentaAutomationService
from apps.bookings.models import BoletoImportado

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
        from core.middleware import agency_context
        # 0. Carga de instancia (Bypass global manager para obtener el objeto inicial)
        boleto = BoletoImportado.all_objects.get(pk=boleto_id)
        
        # 🏢 ACTIVAR CONTEXTO: Crítico para que todos los managers internos funcionen en Celery
        with agency_context(boleto.agencia):
            logger.info(f"🏗️ Contexto Multi-Tenant Activado: {boleto.agencia.nombre} | Procesando Boleto {boleto_id}")
            
            # 🛡️ MODO MANUAL (Review Master Finalization): 
            # Si el usuario ya revisó y editó, NO corremos nada de extracción. Vamos directo a persistencia y venta.
            if manual_only:
                logger.info(f"💾 Guardando cambios manuales para Boleto {boleto_id} (Finalización Directa)")
                
                # 🛡️ FIX: Asegurar que los datos sean un diccionario (evitar 'str' object has no attribute 'get')
                import json
                datos_para_procesar = boleto.datos_parseados or {}
                if isinstance(datos_para_procesar, str):
                    try: datos_para_procesar = json.loads(datos_para_procesar)
                    except Exception as e:
                        logger.warning(f"No se pudo deserializar datos_parseados como JSON: {e}")
                        datos_para_procesar = {}
                    
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
            # Si es ignore_manual=True, forzamos la toma del lock aunque diga PRO
            query = BoletoImportado.all_objects.filter(pk=boleto_id)
            if not ignore_manual:
                query = query.exclude(estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO)
            
            updated_count = query.update(estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO)

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
            
            # 3. 🔥 CACHÉ REDIS: Verificar si ya parseamos texto idéntico
            texto_hash = hashlib.sha256(texto.encode('utf-8', errors='ignore')).hexdigest()
            cache_key = f'parseo_result_{texto_hash}'
            datos = None
            
            if not bypass_cache:
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(f"♻️ Resultado de parseo recuperado de caché Redis (Hash: {texto_hash[:8]}...)")
                    datos = cached_result
            
            # 4. Motor de Parseo: Prioridad IA (Structured Outputs)
            if datos is None:
                path_pdf = None
                try: path_pdf = boleto.archivo_boleto.path
                except Exception as e:
                    logger.warning(f"No se pudo obtener ruta fisica del archivo: {e}")
                
                # 🛡️ ESTRATEGIA: IA PRIMERO (Más estable para formatos complejos)
                try:
                    from apps.automation.parsers.ai_universal_parser import UniversalAIParser
                    from apps.automation.services.ai_engine import QuotaExhaustedException
                    
                    logger.info(f"🧠 Usando IA Primaria (Structured Outputs) para Boleto {boleto_id}...")
                    datos_ia = UniversalAIParser().parse(texto, pdf_path=path_pdf, bypass_cache=bypass_cache)
                    
                    if datos_ia and "error" not in datos_ia:
                        datos = datos_ia
                        logger.info("✅ IA procesó el boleto exitosamente.")
                    else:
                        logger.warning(f"⚠️ IA devolvió error o datos vacíos: {datos_ia.get('error') if datos_ia else 'N/A'}")
                        
                except QuotaExhaustedException:
                    logger.warning(f"🚨 Cuota de IA agotada para agencia {boleto.agencia.nombre}. Usando fallback Regex.")
                except Exception as e_ai:
                    logger.error(f"❌ Fallo crítico en motor de IA: {e_ai}")

                # 🛡️ FALLBACK: REGEX DETERMINÍSTICO (Solo si IA falló o no tiene cuota)
                if datos is None:
                    try:
                        logger.info(f"⚡ Usando Fallback de Regex para Boleto {boleto_id}...")
                        datos_regex = extract_data_from_text(texto, pdf_path=path_pdf, bypass_cache=bypass_cache)
                        if datos_regex and "error" not in datos_regex:
                            datos = datos_regex
                        else:
                            return self._finalize_error(boleto, "Ningún motor (IA/Regex) pudo interpretar el archivo.")
                    except Exception as e_reg:
                        logger.error(f"❌ Error en motor de Regex: {e_reg}")
                        return self._finalize_error(boleto, f"Fallo total de extracción: {e_reg}")
                
                # 4c. Guardar en caché Redis el resultado final (sea IA o Regex)
                if datos and "error" not in datos:
                    try:
                        cache.set(cache_key, datos, timeout=86400)
                        logger.info(f"💾 Resultado guardado en caché Redis (Hash: {texto_hash[:8]}...)")
                    except Exception as e_cache:
                        logger.warning(f"⚠️ Error guardando en caché: {e_cache}")
            
            # 5. Normalización y Procesamiento (Multi-Pax Aware)
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
        """
        Versión Optimizada: Separa operaciones lentas (PDF, AI) de la transacción DB principal.
        """
        try:
            # 1. Fase de Persistencia Base (Rápida)
            with transaction.atomic():
                # A. Persistencia de datos del boleto
                BoletoPersistenceService.update_boleto_from_data(boleto, data)
                BoletoPersistenceService.handle_versioning(boleto)

                # B. Automatización de Venta (Lógica de Negocio)
                venta = VentaAutomationService.crear_venta_desde_parser(
                    parsed_data=data,
                    agencia=boleto.agencia,
                    usuario=None,
                    forced_cliente_id=forced_client_id,
                    boleto_obj=boleto
                )
                
                # Guardamos el estado parcial para liberar el lock de tabla lo antes posible
                boleto.save()

            # 2. Fase de Generación de Archivos (Lenta - FUERA de la transacción)
            # Si Gotenberg falla o Gemini es lento, no bloqueamos la base de datos
            try:
                logger.info(f"📄 Generando TKT PDF para Boleto {boleto.pk}")
                pdf_bytes, fname = PdfGenerationService.generate_ticket(data, agencia_obj=boleto.agencia, boleto_obj=boleto)
                
                if pdf_bytes:
                    from django.core.files.base import ContentFile
                    # Guardamos el archivo físico (operación atómica de FS/Cloudinary)
                    boleto.archivo_pdf_generado.save(fname, ContentFile(pdf_bytes), save=True)
                    logger.info(f"✅ PDF guardado: {fname}")
            except Exception as e_pdf:
                logger.error(f"❌ Error generando PDF (Omitiendo para no fallar el proceso): {e_pdf}")

            # 3. Fase de Cierre (Rápida)
            with transaction.atomic():
                boleto.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO
                boleto.log_parseo = f"Completado exitosamente. Venta ID: {venta.pk if venta else 'N/A'}"
                boleto.save(update_fields=['estado_parseo', 'log_parseo'])

                # Notificación de éxito
                self._notify_success(venta)
            
            # 4. Notificaciones Async (WhatsApp)
            if venta and venta.cliente and getattr(venta.cliente, 'telefono_principal', None):
                self._trigger_whatsapp(venta, boleto)

            return venta

        except Exception as e:
            logger.error(f"🔥 Error crítico en _process_single_ticket: {e}", exc_info=True)
            return self._finalize_error(boleto, f"Error en procesamiento final: {e}")

    def _trigger_whatsapp(self, venta, boleto):
        try:
            from core.tasks import enviar_notificacion_whatsapp_task
            mensaje_ws = f"¡Hola {venta.cliente.nombres}! ✈️ Tu boleto para {venta.localizador} ha sido procesado con éxito. Te adjuntamos el PDF oficial de {boleto.agencia.nombre_comercial or boleto.agencia.nombre}."
            
            pdf_url = boleto.archivo_pdf_generado.url if boleto.archivo_pdf_generado else None
            
            enviar_notificacion_whatsapp_task.delay(
                numero_cliente=getattr(venta.cliente, 'telefono_principal', None) or getattr(venta.cliente, 'telefono_secundario', None),
                mensaje=mensaje_ws,
                email_cliente=venta.cliente.email,
                agencia_id=boleto.agencia.pk,
                media_url=pdf_url,
                file_name=f"Boleto_{venta.localizador}.pdf"
            )
        except Exception as e_ws:
            logger.error(f"❌ Error encolando WhatsApp: {e_ws}")

    def _finalize_error(self, boleto, error_msg):
        logger.error(f"❌ Error Boleto {boleto.pk}: {error_msg}")
        boleto.estado_parseo = 'ERR'
        boleto.log_parseo = error_msg
        boleto.save()
        return None

    def _notify_success(self, venta):
        if not venta: return
        try:
            from apps.automation.models import NotificacionAgente
            if hasattr(venta, 'creado_por') and venta.creado_por:
                NotificacionAgente.objects.create(
                    usuario=venta.creado_por,
                    tipo='ai_magic',
                    titulo='Procesamiento Exitoso ✨',
                    mensaje=f"PNR {venta.localizador} integrado correctamente.",
                    icono='auto_awesome'
                )
        except Exception as e:
            logger.warning(f"Error creando notificacion de exito para venta: {e}")

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
    from apps.automation.parsers.pdf_generation import PdfGenerationService
    return PdfGenerationService.generate_ticket(data, agencia_obj, boleto_obj)


def _parse_sabre_ticket(plain_text: str):
    from apps.automation.parsers.ticket_parser import extract_data_from_text
    data = extract_data_from_text(plain_text)

    if 'error' in data:
        return data

    nombre = data.get('nombre_pasajero', '')
    if '/' in nombre:
        parts = nombre.split('/')
        passenger_name = f"{parts[1].strip()} {parts[0].strip()}"
    else:
        passenger_name = nombre

    normalized = {
        'passenger_name': passenger_name,
        'ticket_number': data.get('numero_boleto', ''),
        'reservation_code': data.get('codigo_reserva', ''),
        'airline_name': data.get('aerolinea_emisora', ''),
        'issuing_agent': data.get('agente', ''),
        'segments': []
    }

    flights = data.get('flights', [])
    for f in flights:
        normalized['segments'].append({
            'flight_number': f.get('vuelo', f.get('flightNumber', '')),
            'origin': f.get('origen', ''),
            'destination': f.get('destino', ''),
            'departure_date_iso': f.get('fecha_salida', ''),
            'departure_time': f.get('hora_salida', ''),
            'arrival_time': f.get('hora_llegada', '')
        })

    return {'SOURCE_SYSTEM': 'SABRE', 'normalized': normalized}
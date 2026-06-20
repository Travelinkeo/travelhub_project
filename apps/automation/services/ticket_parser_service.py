# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE (REFACTORED)
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------
import hashlib
import locale
import logging
import time

logger = logging.getLogger(__name__)

# 🛡️ SAFE LOCALE MONKEY PATCH (SRE L3)
# Intercepts setlocale globally to prevent "unsupported locale setting" crash
try:
    original_setlocale = locale.setlocale

    def safe_setlocale(category, locale_name=None):
        try:
            return original_setlocale(category, locale_name)
        except Exception as e:
            logger.warning(f"⚠️ [SRE L3] Blocked unsupported locale setting '{locale_name}': {e}")
            try:
                return original_setlocale(category, "")
            except Exception:
                try:
                    return original_setlocale(category, "C")
                except Exception:
                    return "C"

    locale.setlocale = safe_setlocale
    logger.info("✅ [SRE L3] Global locale.setlocale monkey patch applied successfully.")
except Exception as e_patch:
    logger.error(f"❌ [SRE L3] Failed to apply locale monkey patch: {e_patch}")

from django.core.cache import cache  # noqa: E402
from django.db import OperationalError, transaction  # noqa: E402

# SUB-SERVICES
from apps.automation.parsers.extraction import ExtractionService  # noqa: E402
from apps.automation.parsers.normalization import DataNormalizationService  # noqa: E402
from apps.automation.parsers.pdf_generation import PdfGenerationService  # noqa: E402
from apps.automation.parsers.persistence import BoletoPersistenceService  # noqa: E402
from apps.automation.parsers.ticket_parser import extract_data_from_text  # noqa: E402
from apps.automation.services.venta_automation import VentaAutomationService  # noqa: E402
from apps.bookings.models import BoletoImportado  # noqa: E402


def _is_celery_available() -> bool:
    """
    Comprueba si el broker de Celery (Redis) está accesible.
    Usado para decidir si generar PDF síncronamente (dev) o asíncronamente (prod).
    """
    try:
        from django.conf import settings

        broker_url = getattr(settings, "CELERY_BROKER_URL", None) or getattr(
            settings, "BROKER_URL", None
        )
        if not broker_url or "memory" in str(broker_url):
            return False
        import redis

        client = redis.from_url(broker_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


def _generate_pdf_sync(boleto) -> None:
    """
    Genera el PDF de un boleto de forma síncrona usando WeasyPrint.
    Siempre disponible — no depende de Celery, Redis ni Gotenberg.
    Tiempo típico: 1-5 segundos.
    """
    from django.core.files.base import ContentFile

    try:
        if boleto.archivo_pdf_generado:
            logger.info(f"⏭️ [SYNC] PDF ya existe para boleto {boleto.pk}, omitiendo.")
            return
        if not boleto.datos_parseados:
            logger.warning(
                f"⚠️ [SYNC] Boleto {boleto.pk} no tiene datos_parseados. No se puede generar PDF."
            )
            BoletoImportado.all_objects.filter(pk=boleto.pk).update(
                estado_parseo="ERR",
                log_parseo=(str(boleto.log_parseo or ""))
                + " | Sin datos para generar PDF. Vuelve a parsear.",
            )
            return

        datos_norm = DataNormalizationService.normalize_ticket_data(boleto.datos_parseados)
        pdf_bytes, fname = PdfGenerationService.generate_ticket(
            datos_norm, agencia_obj=boleto.agencia, boleto_obj=boleto
        )
        if pdf_bytes and len(pdf_bytes) > 100:
            boleto.archivo_pdf_generado.save(fname, ContentFile(pdf_bytes), save=True)
            logger.info(f"✅ [SYNC] PDF generado correctamente: {fname} ({len(pdf_bytes):,} bytes)")
        else:
            # PDF vacío — WeasyPrint corrió pero no produjo bytes útiles
            logger.error(
                f"❌ [SYNC] PDF vacío ({len(pdf_bytes) if pdf_bytes else 0} bytes) para boleto {boleto.pk}. "
                "Posible fallo de WeasyPrint o plantilla HTML con error."
            )
            BoletoImportado.all_objects.filter(pk=boleto.pk).update(
                estado_parseo="ERR",
                log_parseo=(str(boleto.log_parseo or ""))
                + " | PDF vacío generado. Usa el botón Reintentar.",
            )
    except Exception as e:
        logger.error(f"❌ [SYNC] Error generando PDF para boleto {boleto.pk}: {e}", exc_info=True)
        # Registrar el error en el log del boleto para que sea visible en la UI
        try:
            BoletoImportado.all_objects.filter(pk=boleto.pk).update(
                estado_parseo="ERR",
                log_parseo=(str(boleto.log_parseo or "")) + f" | Error en PDF: {str(e)[:300]}",
            )
        except Exception as e_log:
            logger.error(f"No se pudo actualizar log_parseo del boleto {boleto.pk}: {e_log}")


# =========================================================================================
# 🏢 EXPLICACIÓN PARA TODO PÚBLICO (Inversores y No Programadores)
# Imagine que recibe cartas de amor escritas a mano en diferentes idiomas, estilos y caligrafías,
# y necesita extraer de cada una: la fecha de la cita, el remitente y cuánto costó el regalo.
# Este servicio es como contratar a un asistente ultra inteligente (la Inteligencia Artificial de Google Gemini)
# que lee cada carta, entiende el contexto y extrae exactamente lo que necesita en una tabla limpia.
#
# Y si por alguna razón el asistente se va a almorzar o el teléfono no tiene señal (caída de red/API),
# el sistema cuenta con un "Manual de Emergencias" (expresiones regulares o Regex) para buscar de
# manera tradicional patrones exactos de texto (como buscar la palabra "Pasajero:" seguida de letras).
# Esto asegura que el negocio nunca se detenga y la facturación siga su curso.
#
# 💻 EXPLICACIÓN PARA PROGRAMADORES (Technical Specs)
# TicketParserService es el core pipeline orquestador de ingesta de datos semiestructurados.
# Diseñado con un patrón Híbrido:
#   1. Intenta extracción semántica zero-shot usando Google Gemini AI (API v1.5 Pro/Flash).
#   2. Si falla por cuota (rate limits/429) o fallos de red, activa el Engine de Respaldo por Regex.
#   3. Normaliza las fechas, monedas y nombres de aerolíneas usando DataNormalizationService.
#   4. Aplica persistencia transaccional y dispara VentaAutomationService para generar la venta,
#      el cliente, los ítems y calcular los márgenes e impuestos automáticamente.
# =========================================================================================
class TicketParserService:
    """
    🏢 MULTI-TENANT | 🧠 ORQUESTADOR | 🚨 CRÍTICO
    Punto de entrada unificado para el procesamiento de boletos.
    Coordina la extracción, normalización, persistencia y automatización financiera.
    """

    def process_boleto(self, boleto, forced_client_id=None, ignore_manual=False):
        """Bridge alias method to handle direct Boleto object calls from external modules."""
        res = self.procesar_boleto(
            boleto_id=boleto.pk, forced_client_id=forced_client_id, ignore_manual=ignore_manual
        )

        # 🛡️ Guardia Anti-Huérfano: Solo actúa si el boleto se quedó en 'PRO' (crash durante procesamiento)
        # _process_single_ticket ya gestiona COM/REV correctamente, NO sobreescribimos aquí
        try:
            boleto.refresh_from_db()
            if boleto.estado_parseo == "PRO":  # Stuck in processing = crash happened
                boleto.estado_parseo = "REV"
                boleto.log_parseo = (
                    boleto.log_parseo or ""
                ) + " | Estado huérfano detectado y corregido."
                boleto.save(update_fields=["estado_parseo", "log_parseo"])
                logger.warning(
                    f"⚠️ [SRE] process_boleto: Boleto {boleto.pk} estaba atascado en PRO. Corregido a REV."
                )
        except Exception as e:
            logger.error(f"❌ [SRE] Error en guardia anti-huérfano de process_boleto: {e}")

        return res

    def procesar_boleto(
        self,
        boleto_id,
        forced_client_id=None,
        ignore_manual=False,
        bypass_cache=False,
        manual_only=False,
    ):
        """Pipeline principal con lógica de reintentos para evitar deadlocks."""
        max_retries = 3
        retry_delay = 1

        start_time = time.time()
        for attempt in range(max_retries):
            try:
                result = self._run_pipeline(
                    boleto_id, forced_client_id, ignore_manual, bypass_cache, manual_only
                )
                duration = time.time() - start_time
                logger.info(
                    f"⏱️ [PROFILING] Pipeline TOTAL para boleto {boleto_id}: {duration:.2f}s"
                )
                return result

            except OperationalError as e:
                if any(err in str(e).lower() for err in ["deadlock", "database is locked"]):
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"🔄 Reintentando por bloqueo de DB ({attempt + 1}/{max_retries})..."
                        )
                        time.sleep(retry_delay)
                        continue
                raise
            except BaseException as e:
                logger.exception(
                    f"❌ Fallo crítico/Timeout (BaseException) en pipeline para boleto {boleto_id}: {e}"
                )
                # 🛡️ EMERGENCIA: Evitar que el boleto se quede en estado 'PRO' (En Proceso) para siempre
                try:
                    from apps.bookings.models import BoletoImportado

                    BoletoImportado.all_objects.filter(pk=boleto_id).update(
                        estado_parseo="REV",  # REVISION_REQUERIDA (max_length=3)
                        log_parseo=f"Fallo Crítico/Timeout: {str(e)[:500]}",
                    )
                    logger.warning(
                        "⚠️ [SRE L3] procesar_boleto: Emergencia activada, sellado como REV."
                    )
                except Exception as e_inner:
                    logger.error(f"No se pudo marcar boleto como REV: {e_inner}")
                raise

    def _run_pipeline(
        self, boleto_id, forced_client_id, ignore_manual, bypass_cache=False, manual_only=False
    ):
        from core.api import agency_context

        # 0. Carga de instancia (Bypass global manager para obtener el objeto inicial)
        boleto = BoletoImportado.all_objects.get(pk=boleto_id)

        # 🏢 ACTIVAR CONTEXTO: Crítico para que todos los managers internos funcionen en Celery
        with agency_context(boleto.agencia):
            logger.info(
                f"🏗️ Contexto Multi-Tenant Activado: {boleto.agencia.nombre} | Procesando Boleto {boleto_id}"
            )

            # 🛡️ MODO MANUAL (Review Master Finalization):
            # Si el usuario ya revisó y editó, NO corremos nada de extracción. Vamos directo a persistencia y venta.
            if manual_only:
                logger.info(
                    f"💾 Guardando cambios manuales para Boleto {boleto_id} (Finalización Directa)"
                )

                # 🛡️ FIX: Asegurar que los datos sean un diccionario (evitar 'str' object has no attribute 'get')
                import json

                datos_para_procesar = boleto.datos_parseados or {}
                if isinstance(datos_para_procesar, str):
                    try:
                        datos_para_procesar = json.loads(datos_para_procesar)
                    except Exception as e:
                        logger.warning(f"No se pudo deserializar datos_parseados como JSON: {e}")
                        datos_para_procesar = {}

                datos_norm = DataNormalizationService.normalize_ticket_data(datos_para_procesar)
                return self._process_single_ticket(boleto, datos_norm, forced_client_id)

            # 🧠 INTELIGENCIA DE REUTILIZACIÓN: Si ya tenemos datos y no se forzó el re-parseo, los usamos.
            if (
                not ignore_manual
                and boleto.datos_parseados
                and isinstance(boleto.datos_parseados, dict)
            ):
                has_basics = boleto.datos_parseados.get("pnr") or boleto.datos_parseados.get(
                    "passenger_name"
                )
                if has_basics:
                    logger.info(
                        f"♻️ Reutilizando datos existentes para Boleto {boleto_id} (Studio Mode)"
                    )
                    datos_norm = DataNormalizationService.normalize_ticket_data(
                        boleto.datos_parseados
                    )
                    return self._process_single_ticket(boleto, datos_norm, forced_client_id)

            # 1. Adquisición de Lock Atómico
            # Evitamos que dos procesos (Signal vs View vs Celery) procesen lo mismo simultáneamente.
            # Si es ignore_manual=True, forzamos la toma del lock aunque diga PRO
            query = BoletoImportado.all_objects.filter(pk=boleto_id)
            if not ignore_manual:
                query = query.exclude(estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO)

            updated_count = query.update(estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO)

            if updated_count == 0:
                logger.info(
                    f"⏭️ Boleto {boleto_id} ya está siendo procesado por otro hilo. Esperando..."
                )
                boleto.refresh_from_db()
                return boleto.venta_asociada or True

            boleto.log_parseo = "Iniciando pipeline de extracción..."
            boleto.save(update_fields=["log_parseo"])

            # 2. Extracción de Texto
            raw_file = ExtractionService.get_open_file(boleto)
            try:
                texto = ExtractionService.extract_text(raw_file, boleto.archivo_boleto.name)
            finally:
                if raw_file:
                    raw_file.close()

            if not texto:
                return self._finalize_error(boleto, "Archivo vacío o ilegible.")

            # 3. 🔥 CACHÉ REDIS: Verificar si ya parseamos texto idéntico
            texto_hash = hashlib.sha256(texto.encode("utf-8", errors="ignore")).hexdigest()
            cache_key = f"parseo_result_{texto_hash}"
            datos = None

            if not bypass_cache:
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(
                        f"♻️ Resultado de parseo recuperado de caché Redis (Hash: {texto_hash[:8]}...)"
                    )
                    datos = cached_result

            # 4. Motor de Parseo: Prioridad IA (Structured Outputs)
            if datos is None:
                path_pdf = None
                try:
                    path_pdf = boleto.archivo_boleto.path
                except Exception as e:
                    logger.warning(f"No se pudo obtener ruta fisica del archivo: {e}")

                # ⚡ PASO 1: INTENTAR REGEX/GDS LOCAL PRIMERO (Fast-First)
                try:
                    logger.info(f"⚡ Usando Motor Regex/GDS Local para Boleto {boleto_id}...")
                    regex_start = time.time()
                    datos_regex = extract_data_from_text(
                        texto, pdf_path=path_pdf, bypass_cache=bypass_cache
                    )
                    regex_duration = time.time() - regex_start
                    logger.info(f"⏱️ [PROFILING] Regex parse duration: {regex_duration:.2f}s")

                    # Validación de Contrato de Calidad Mínimo para evitar pasar a la IA
                    if datos_regex and not datos_regex.get("error"):
                        if datos_regex.get("is_multi_pax"):
                            tickets_list = datos_regex.get("tickets", [])
                            has_all_pax = len(tickets_list) > 0 and all(
                                t.get("NOMBRE_DEL_PASAJERO") or t.get("passenger_name")
                                for t in tickets_list
                            )
                            has_pnr = all(
                                t.get("CODIGO_RESERVA") or t.get("pnr") or t.get("codigo_reserva")
                                for t in tickets_list
                            )
                            has_flights = all(
                                len(
                                    t.get("vuelos", [])
                                    or t.get("flights", [])
                                    or t.get("segmentos", [])
                                )
                                > 0
                                for t in tickets_list
                            )
                            has_times = all(
                                any(
                                    f.get("hora_salida")
                                    or f.get("hora_llegada")
                                    or (
                                        isinstance(f.get("departure"), dict)
                                        and f.get("departure").get("time")
                                    )
                                    for f in (
                                        t.get("vuelos", [])
                                        or t.get("flights", [])
                                        or t.get("segmentos", [])
                                    )
                                )
                                for t in tickets_list
                            )
                            is_regex_reliable = (
                                has_all_pax and has_pnr and has_flights and has_times
                            )
                        else:
                            has_pax = bool(
                                datos_regex.get("passenger_name")
                                or datos_regex.get("nombre_pasajero")
                            )
                            has_pnr = bool(
                                datos_regex.get("pnr")
                                or datos_regex.get("codigo_reserva")
                                or datos_regex.get("localizador")
                            )
                            flights_list = (
                                datos_regex.get("segments", [])
                                or datos_regex.get("segmentos", [])
                                or datos_regex.get("flights", [])
                                or datos_regex.get("vuelos", [])
                            )
                            has_flights = len(flights_list) > 0
                            has_times = any(
                                f.get("hora_salida")
                                or f.get("hora_llegada")
                                or (
                                    isinstance(f.get("departure"), dict)
                                    and f.get("departure").get("time")
                                )
                                for f in flights_list
                            )
                            is_regex_reliable = has_pax and has_pnr and has_flights and has_times

                        if is_regex_reliable:
                            datos = datos_regex
                            logger.info(
                                "✅ Extracción exitosa y completa con motor Regex/GDS local."
                            )
                            boleto.log_parseo = "Regex/GDS local exitoso (completo)."
                            boleto.save(update_fields=["log_parseo"])
                        else:
                            logger.info(
                                "⚠️ Regex local incompleto o no verificado. Se requiere fallback a IA."
                            )
                    else:
                        logger.info(
                            "⚠️ Regex local no pudo parsear el archivo. Se requiere fallback a IA."
                        )
                except Exception as e_reg:
                    logger.error(f"❌ Error en motor de Regex: {e_reg}")
                    boleto.log_parseo = f"Error en Regex local: {str(e_reg)}. Intentando IA..."
                    boleto.save(update_fields=["log_parseo"])

                # 🧠 PASO 2: FALLBACK A IA (Solo si el regex no fue suficiente o confiable)
                if datos is None:
                    try:
                        from apps.automation.parsers.ai_universal_parser import UniversalAIParser
                        from apps.automation.services.ai_engine import QuotaExhaustedException

                        logger.info(
                            f"🧠 Usando IA Primaria (Structured Outputs) de Fallback para Boleto {boleto_id}..."
                        )
                        ai_start = time.time()
                        datos_ia = UniversalAIParser().parse(
                            texto, pdf_path=path_pdf, bypass_cache=bypass_cache
                        )
                        ai_duration = time.time() - ai_start
                        logger.info(f"⏱️ [PROFILING] IA Engine parse duration: {ai_duration:.2f}s")

                        if datos_ia and "error" not in datos_ia:
                            datos = datos_ia
                            logger.info("✅ IA de Fallback procesó el boleto exitosamente.")
                            boleto.log_parseo = (
                                boleto.log_parseo or ""
                            ) + " | IA de Fallback exitosa."
                            boleto.save(update_fields=["log_parseo"])
                        else:
                            error_detail = (
                                datos_ia.get("status_detail") or datos_ia.get("error")
                                if datos_ia
                                else "Unknown Error"
                            )
                            logger.warning(f"⚠️ IA devolvió error o datos vacíos: {error_detail}")
                            # Si IA falló, intentamos usar los datos parciales de regex
                            if (
                                "datos_regex" in locals()
                                and datos_regex
                                and not datos_regex.get("error")
                            ):
                                datos = datos_regex
                                datos["_requiere_revision"] = True
                                logger.info(
                                    "⚠️ Recuperando datos parciales de Regex ante fallo de IA."
                                )
                                boleto.log_parseo = (
                                    boleto.log_parseo or ""
                                ) + f" | IA Falló: {error_detail}. Usando datos parciales de Regex."
                                boleto.save(update_fields=["log_parseo"])
                            else:
                                msg_error = f"Parseo Inteligente falló: {error_detail}"
                                return self._finalize_error(boleto, msg_error)

                    except QuotaExhaustedException:
                        logger.warning(
                            f"🚨 Cuota de IA agotada para agencia {boleto.agencia.nombre}."
                        )
                        if (
                            "datos_regex" in locals()
                            and datos_regex
                            and not datos_regex.get("error")
                        ):
                            datos = datos_regex
                            datos["_requiere_revision"] = True
                            boleto.log_parseo = (
                                boleto.log_parseo or ""
                            ) + " | Cuota IA agotada. Usando datos parciales de Regex."
                            boleto.save(update_fields=["log_parseo"])
                        else:
                            return self._finalize_error(
                                boleto, "Cuota de IA agotada y sin datos de Regex."
                            )
                    except Exception as e_ai:
                        logger.error(f"❌ Fallo crítico en motor de IA: {e_ai}")
                        if (
                            "datos_regex" in locals()
                            and datos_regex
                            and not datos_regex.get("error")
                        ):
                            datos = datos_regex
                            datos["_requiere_revision"] = True
                            boleto.log_parseo = (
                                boleto.log_parseo or ""
                            ) + f" | Error IA: {str(e_ai)}. Usando datos parciales de Regex."
                            boleto.save(update_fields=["log_parseo"])
                        else:
                            return self._finalize_error(
                                boleto, f"Error en motor de IA de Fallback: {str(e_ai)}"
                            )

                # 4c. Guardar en caché Redis el resultado final (sea IA o Regex)
                if datos and "error" not in datos:
                    try:
                        cache.set(cache_key, datos, timeout=86400)
                        logger.info(
                            f"💾 Resultado guardado en caché Redis (Hash: {texto_hash[:8]}...)"
                        )
                    except Exception as e_cache:
                        logger.warning(f"⚠️ Error guardando en caché: {e_cache}")

            # 5. Normalización y Procesamiento (Multi-Pax Aware)
            if isinstance(datos, dict) and datos.get("is_multi_pax"):
                tickets = datos.get("tickets", [])
                logger.info(
                    f"👨‍👩‍👧‍👦 Grupo detectado: {len(tickets)} pasajeros. Iniciando Split Atómico..."
                )

                from apps.bookings.models import BoletoImportadoTransito

                try:
                    with transaction.atomic():
                        # 1. Crear registros de tránsito para asegurar que todo el grupo está staged
                        transito_records = []
                        for i, ticket_data in enumerate(tickets):
                            tr = BoletoImportadoTransito.objects.create(
                                boleto_origen=boleto,
                                agencia=boleto.agencia,
                                ticket_index=i,
                                nombre_pasajero=ticket_data.get("passenger_name"),
                                numero_boleto=ticket_data.get("ticket_number"),
                                datos_json=ticket_data,
                                procesado=False,
                            )
                            transito_records.append(tr)

                        logger.info(
                            f"Staged {len(transito_records)} pasajeros en BoletoImportadoTransito."
                        )

                        # 2. Procesar el primer boleto (usa la instancia actual)
                        first_tr = transito_records[0]
                        first_ticket_data = DataNormalizationService.normalize_ticket_data(
                            first_tr.datos_json
                        )
                        venta_maestra = self._process_single_ticket(
                            boleto, first_ticket_data, forced_client_id
                        )
                        first_tr.procesado = True
                        first_tr.save(update_fields=["procesado"])

                        # 3. Procesar los siguientes creando nuevas instancias de BoletoImportado
                        for tr in transito_records[1:]:
                            logger.info(
                                f"👤 Creando instancia para pasajero adicional {tr.nombre_pasajero} (Ticket {tr.ticket_index + 1})..."
                            )
                            create_kwargs = {
                                "archivo_boleto": boleto.archivo_boleto,
                                "agencia": boleto.agencia,
                                "estado_parseo": "PEN",
                            }
                            if hasattr(boleto, "creado_por"):
                                create_kwargs["creado_por"] = boleto.creado_por
                            nuevo_boleto = BoletoImportado.objects.create(**create_kwargs)
                            norm_data = DataNormalizationService.normalize_ticket_data(
                                tr.datos_json
                            )
                            self._process_single_ticket(nuevo_boleto, norm_data, forced_client_id)
                            tr.procesado = True
                            tr.save(update_fields=["procesado"])

                    return venta_maestra
                except Exception as e_multi:
                    logger.error(
                        f"❌ Error atómico durante el splitting del grupo: {e_multi}", exc_info=True
                    )
                    # En caso de error, el estado del boleto principal se marcará como error
                    return self._finalize_error(
                        boleto, f"Error en Split Atómico de Pasajeros: {str(e_multi)}"
                    )

            # Procesamiento estándar (Single Pax)
            requiere_revision = bool(
                datos.get("_requiere_revision", False)
            )  # Flag de datos parciales
            datos_norm = DataNormalizationService.normalize_ticket_data(datos)
            datos_norm["_requiere_revision"] = (
                requiere_revision  # Preservar flag después de normalización
            )
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
                    boleto_obj=boleto,
                )

                # Guardamos el estado parcial para liberar el lock de tabla lo antes posible
                boleto.save()

            # 2. Fase de Generación de PDF
            # Si Celery/Redis están disponibles → async. Si no → síncrono directo para
            # garantizar que el PDF exista cuando el usuario abra la vista de revisión.
            pdf_sync_failed = False
            try:
                from apps.common.utils.celery_utils import _is_celery_available

                if _is_celery_available():
                    logger.info(
                        f"📄 Encolando generación de PDF (async) para Boleto {boleto.pk}..."
                    )
                    from apps.common.utils.celery_utils import safe_delay
                    from core.tasks import generar_pdf_ticket_async_task

                    safe_delay(generar_pdf_ticket_async_task, boleto.pk)
                else:
                    logger.info(
                        f"📄 Celery no disponible — generando PDF síncronamente para Boleto {boleto.pk}..."
                    )
                    _generate_pdf_sync(boleto)
                    boleto.refresh_from_db()
                    if not boleto.archivo_pdf_generado:
                        pdf_sync_failed = True
            except Exception as e_pdf_gen:
                logger.error(f"❌ Error en generación de PDF para Boleto {boleto.pk}: {e_pdf_gen}")
                pdf_sync_failed = True
                # Último recurso: intentar generación síncrona
                try:
                    _generate_pdf_sync(boleto)
                    boleto.refresh_from_db()
                    if boleto.archivo_pdf_generado:
                        pdf_sync_failed = False
                except Exception as e_sync:
                    logger.error(
                        f"❌ Fallo total en generación de PDF (sync fallback) para Boleto {boleto.pk}: {e_sync}"
                    )

            # 3. Fase de Cierre (Rápida)
            with transaction.atomic():
                # Si el PDF síncrono falló, cerrar como REV para que el usuario reintente
                if pdf_sync_failed:
                    boleto.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                    boleto.log_parseo = "PDF no generado. Revisa los datos y usa 'Reintentar PDF'."
                    logger.warning(f"⚠️ Boleto {boleto.pk} cerrado como REV (PDF falló).")
                elif bool(data.get("_requiere_revision", False)):
                    boleto.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA  # 'REV'
                    boleto.log_parseo = "Datos parciales (sin segmentos de vuelo). PDF generado. Revisa el itinerario."
                    logger.warning(
                        f"⚠️ Boleto {boleto.pk} cerrado como REV (datos parciales). PDF generado correctamente."
                    )
                else:
                    boleto.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO  # 'COM'
                    boleto.log_parseo = (
                        f"Completado exitosamente. Venta ID: {venta.pk if venta else 'N/A'}"
                    )
                    logger.info(
                        f"✅ Boleto {boleto.pk} cerrado como COM. Venta: {venta.pk if venta else 'N/A'}"
                    )
                boleto.save(update_fields=["estado_parseo", "log_parseo"])

                # Notificación de éxito
                self._notify_success(venta)

            # 4. Notificaciones Async (WhatsApp)
            if venta and venta.cliente and getattr(venta.cliente, "telefono_principal", None):
                self._trigger_whatsapp(venta, boleto)

            return venta

        except Exception as e:
            logger.error(f"🔥 Error crítico en _process_single_ticket: {e}", exc_info=True)
            return self._finalize_error(boleto, f"Error en procesamiento final: {e}")

    def _trigger_whatsapp(self, venta, boleto):
        try:
            from core.api import enviar_notificacion_whatsapp_task

            mensaje_ws = f"¡Hola {venta.cliente.nombres}! ✈️ Tu boleto para {venta.localizador} ha sido procesado con éxito. Te adjuntamos el PDF oficial de {boleto.agencia.nombre_comercial or boleto.agencia.nombre}."

            def enqueue_whatsapp(
                num=None,
                msg=mensaje_ws,
                email=venta.cliente.email,
                a_pk=boleto.agencia.pk,
                b_pk=boleto.pk,
                loc=venta.localizador,
            ):
                if num is None:
                    num = getattr(venta.cliente, "telefono_principal", None) or getattr(
                        venta.cliente, "telefono_secundario", None
                    )
                # Retrieve fresh boleto object in task to fetch the generated PDF URL
                fresh_b = BoletoImportado.objects.filter(pk=b_pk).first()
                p_url = (
                    fresh_b.archivo_pdf_generado.url
                    if fresh_b and fresh_b.archivo_pdf_generado
                    else None
                )
                enviar_notificacion_whatsapp_task.delay(
                    numero_cliente=num,
                    mensaje=msg,
                    email_cliente=email,
                    agencia_id=a_pk,
                    media_url=p_url,
                    file_name=f"Boleto_{loc}.pdf",
                )

            transaction.on_commit(enqueue_whatsapp)
        except Exception as e_ws:
            logger.error(f"❌ Error encolando WhatsApp en on_commit: {e_ws}")

    def _finalize_error(self, boleto, error_msg):
        logger.error(f"❌ Error Boleto {boleto.pk}: {error_msg}")
        # Si ya está marcado como REV (Revisión Requerida), lo mantenemos
        # De lo contrario, marcamos como ERR
        if boleto.estado_parseo not in ("REV", "ERR"):
            boleto.estado_parseo = "REV"  # Preferimos REV para que el usuario pueda corregir
        if boleto.log_parseo:
            boleto.log_parseo = f"{boleto.log_parseo} | {str(error_msg)}"[:2000]
        else:
            boleto.log_parseo = str(error_msg)[:2000]  # Truncar para no sobrepasar el campo
        try:
            boleto.save(update_fields=["estado_parseo", "log_parseo"])
        except Exception as e_save:
            logger.error(f"❌ Error guardando estado de error en boleto {boleto.pk}: {e_save}")
            try:
                BoletoImportado.all_objects.filter(pk=boleto.pk).update(
                    estado_parseo="ERR", log_parseo=str(error_msg)[:200]
                )
            except Exception as e_final:
                logger.error(f"Error final en boleto {boleto.pk}: {e_final}")
        return None

    def _notify_success(self, venta):
        if not venta:
            return
        try:
            from apps.automation.models import NotificacionAgente

            if hasattr(venta, "creado_por") and venta.creado_por:
                NotificacionAgente.objects.create(
                    usuario=venta.creado_por,
                    tipo="ai_magic",
                    titulo="Procesamiento Exitoso ✨",
                    mensaje=f"PNR {venta.localizador} integrado correctamente.",
                    icono="auto_awesome",
                )
        except Exception as e:
            logger.warning(f"Error creando notificacion de exito para venta: {e}")

    def _extraer_texto(self, boleto):
        """Bridge for legacy code (ReviewBoletoView)"""
        raw_file = ExtractionService.get_open_file(boleto)
        try:
            return ExtractionService.extract_text(raw_file, boleto.archivo_boleto.name)
        finally:
            if raw_file:
                raw_file.close()


# -----------------------------------------------------
# 🏛️ LEGACY COMPATIBILITY LAYER
# -----------------------------------------------------
def orquestar_parseo_de_boleto(boleto_id, forced_client_id=None, ignore_manual=False):
    """Bridge for legacy code (views_legacy.py, etc.)"""
    return TicketParserService().procesar_boleto(boleto_id, forced_client_id, ignore_manual)


# Mock para compatibilidad
def generar_pdf_en_memoria(data, agencia_obj=None, boleto_obj=None):
    return PdfGenerationService.generate_ticket(data, agencia_obj, boleto_obj)


def _parse_sabre_ticket(plain_text: str):
    from apps.automation.parsers.ticket_parser import extract_data_from_text

    data = extract_data_from_text(plain_text)

    if "error" in data:
        return data

    nombre = (
        data.get("nombre_pasajero")
        or data.get("passenger_name")
        or data.get("NOMBRE DEL PASAJERO", "")
    )
    if "/" in nombre:
        parts = nombre.split("/")
        passenger_name = f"{parts[1].strip()} {parts[0].strip()}"
    else:
        passenger_name = nombre

    # Limpiar títulos comunes en el nombre del pasajero para compatibilidad
    import re

    passenger_name = re.sub(
        r"\s+(MR|MRS|MS|MSTR|MISS|M|F)$", "", passenger_name, flags=re.IGNORECASE
    )

    ticket_num = (
        data.get("ticket_number") or data.get("NUMERO DE BOLETO") or data.get("numero_boleto", "")
    )
    res_code = data.get("codigo_reserva") or data.get("CODIGO RESERVA") or data.get("pnr", "")
    airline = (
        data.get("aerolinea_emisora")
        or data.get("NOMBRE AEROLINEA")
        or data.get("nombre_aerolinea", "")
    )
    agent = data.get("agente") or data.get("AGENTE EMISOR") or data.get("agente_emisor", "")

    # Extraer fecha de emisión ISO
    from apps.automation.parsers.parsing_utils import _fecha_a_iso, _formatear_fecha_dd_mm_yyyy

    raw_issue_date = (
        data.get("fecha_emision_iso")
        or data.get("FECHA DE EMISION")
        or data.get("fecha_emision", "")
    )
    issue_date_iso = _fecha_a_iso(_formatear_fecha_dd_mm_yyyy(raw_issue_date)) or raw_issue_date

    normalized = {
        "passenger_name": passenger_name,
        "ticket_number": ticket_num,
        "reservation_code": res_code,
        "airline_name": airline,
        "issuing_agent": agent,
        "issuing_date_iso": issue_date_iso,
        "segments": [],
    }

    flights = data.get("vuelos") or data.get("flights") or data.get("segmentos") or []
    for f in flights:
        if not isinstance(f, dict):
            continue
        vuelo_num = f.get("numero_vuelo") or f.get("vuelo") or f.get("flightNumber", "")

        # Origen / Destino
        origen = f.get("origen", "")
        if isinstance(origen, dict):
            origen = origen.get("ciudad") or origen.get("location", "")

        destino = f.get("destino", "")
        if isinstance(destino, dict):
            destino = destino.get("ciudad") or destino.get("location", "")

        # Fechas
        raw_salida = f.get("fecha_salida_iso") or f.get("fecha_salida") or f.get("date", "")
        f_salida = _fecha_a_iso(_formatear_fecha_dd_mm_yyyy(raw_salida)) or raw_salida

        normalized["segments"].append(
            {
                "flight_number": vuelo_num,
                "origin": origen,
                "destination": destino,
                "departure_date_iso": f_salida,
                "departure_time": f.get("hora_salida") or f.get("departure", {}).get("time", ""),
                "arrival_time": f.get("hora_llegada") or f.get("arrival", {}).get("time", ""),
            }
        )

    return {"SOURCE_SYSTEM": "SABRE", "normalized": normalized}

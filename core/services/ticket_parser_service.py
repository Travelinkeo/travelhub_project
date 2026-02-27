# -*- coding: utf-8 -*-
# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# This service handles the core parsing logic, PDF generation, and Notifications.
# LOGIC IS LOCKED. DO NOT MODIFY WITHOUT EXPLICIT AUTHORIZATION.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------
import logging
import os
import io
import requests
import pdfplumber
from email import policy
from email.parser import BytesParser
from io import BytesIO
from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import transaction, OperationalError
from django.db.models import Sum, Q
from core.middleware import get_current_request_meta
try:
    import pypdf
except ImportError:
    pypdf = None
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# IMPORTS DE MODELOS
try:
    from apps.crm.models import Cliente
except ImportError:
    from core.models import Cliente

try:
    from core.models_catalogos import ProductoServicio
except ImportError:
    from core.models import ProductoServicio

from core.models import BoletoImportado, Venta, ItemVenta, Agencia, Moneda
from core.ticket_parser import extract_data_from_text, generate_ticket

logger = logging.getLogger(__name__)

class TicketParserService:
    """
    Servicio principal para el procesamiento de boletos importados.
    Encargado de la extracción de texto, parseo inteligente,
    generación de ventas, PDFs y gestión de reintentos para deadlocks.

    Methods:
        procesar_boleto(self, boleto_id, forced_client_id=None)
    """

    def procesar_boleto(self, boleto_id, forced_client_id=None):
        """
        Punto de entrada principal para procesar un boleto con reintentos para deadlocks.
        """
        import time
        max_retries = 3
        retry_delay = 1 # segundo
        
        for attempt in range(max_retries):
            try:
                return self._ejecutar_procesamiento_base(boleto_id, forced_client_id)
            except OperationalError as e:
                if "deadlock" in str(e).lower() or "database is locked" in str(e).lower():
                    if attempt < max_retries - 1:
                        logger.warning(f"🔄 Deadlock detectado (Intento {attempt+1}/{max_retries}). Reintentando en {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                raise
            except Exception as e:
                logger.exception(f"❌ Error fatal procesando boleto {boleto_id}: {e}")
                raise

    def _ejecutar_procesamiento_base(self, boleto_id, forced_client_id=None):
        boleto = None
        try:
            boleto = BoletoImportado.objects.get(pk=boleto_id)
            logger.info(f"🔄 Procesando boleto ID {boleto_id}: {boleto.archivo_boleto.name}")

            # 1. Extracción de Texto usando método unificado
            texto_completo = self._extraer_texto(boleto)
            
            if not texto_completo:
                logger.error("❌ Archivo vacío, ilegible o formato no soportado.")
                boleto.estado_parseo = 'ERR'
                boleto.log_parseo = "No se pudo extraer texto del archivo."
                boleto.save()
                return None

            # 2. Parseo Inteligente (Delegado a core.ticket_parser)
            path_pdf = None
            try:
                 if hasattr(boleto.archivo_boleto, 'path'):
                     path_pdf = boleto.archivo_boleto.path
            except:
                 pass
                 
            datos = extract_data_from_text(texto_completo, pdf_path=path_pdf)
            safe_datos_log = str(datos).encode('ascii', 'replace').decode('ascii')
            logger.info(f"📊 Datos detectados: {safe_datos_log}")

            if datos is None:
                logger.error("❌ Error: extract_data_from_text devolvió None")
                datos = {"error": "El parseador devolvió un resultado vacío (None)."}

            if "error" in datos:
                logger.error(f"❌ Error en parseo: {datos['error']}")
                boleto.estado_parseo = 'ERR'
                boleto.log_parseo = datos['error']
                boleto.save()
                return None

            # 3. Guardado/Actualización de Venta
            # 3. Procesamiento Multi-Pax vs Single
            # Si el parser devuelve una estructura multi-pax (lista o dict con 'tickets')
            lista_tickets = []
            if isinstance(datos, dict) and datos.get('is_multi_pax'):
                lista_tickets = datos.get('tickets', [])
            elif isinstance(datos, list):
                lista_tickets = datos
            else:
                lista_tickets = [datos] # Caso tradicional: 1 boleto

            resultados = []
            logger.info(f"📋 Se detectaron {len(lista_tickets)} boletos en el archivo.")

            for i, info_ticket in enumerate(lista_tickets):
                # Clonar el BoletoImportado 'padre' si hay múltiples, o usar el mismo si es uno solo
                boleto_a_procesar = boleto
                if len(lista_tickets) > 1 and i > 0:
                    # Crear copias para los siguientes pasajeros SI NO EXISTEN
                    # Estrategia: Buscar si ya existen hermanos creados en corridas anteriores
                    hermanos = BoletoImportado.objects.filter(
                        archivo_boleto=boleto.archivo_boleto
                    ).exclude(pk=boleto.pk).order_by('pk')
                    
                    # Intentamos reutilizar en orden (asumiendo determinismo del parser)
                    indice_hermano = i - 1
                    if indice_hermano < len(hermanos):
                        boleto_a_procesar = hermanos[indice_hermano]
                        logger.info(f"♻️ Reutilizando hermano existente ID {boleto_a_procesar.pk} para ticket {i}")
                    else:
                        boleto_a_procesar = BoletoImportado.objects.create(
                            archivo_boleto=boleto.archivo_boleto, # Comparten archivo físico
                            estado_parseo='PRO' 
                        )
                        logger.info(f"✨ Creando nuevo hermano para ticket {i}")
                
                # Asegurar que datos es un diccionario
                datos_dict = info_ticket
                if hasattr(info_ticket, 'to_dict'):
                    datos_dict = info_ticket.to_dict()
                
                # --- INYECCIÓN DE DATOS MANUALES (Persistence Fix) ---
                # Si el boleto ya tiene datos manuales (ej: ingresados en vista 'Resolver Pendiente'),
                # estos deben PREVALECER sobre el parser (que probablemente falló y por eso estamos aquí).
                
                # FOID
                if boleto_a_procesar.foid_pasajero and boleto_a_procesar.foid_pasajero != 'None':
                     # Solo sobrescribimos si el parser no trajo nada o trajo basura, O SIEMPRE?
                     # Mejor: Mergear. Si el DB tiene valor, lo imponemos en el dict para que PDF y Venta lo usen.
                     datos_dict['passenger_document'] = boleto_a_procesar.foid_pasajero
                     datos_dict['CODIGO_IDENTIFICACION'] = boleto_a_procesar.foid_pasajero
                     logger.info(f"💉 Inyectando FOID manual '{boleto_a_procesar.foid_pasajero}' al dataset.")

                # Nombre Pasajero
                if boleto_a_procesar.nombre_pasajero_procesado and boleto_a_procesar.nombre_pasajero_procesado != 'None':
                     datos_dict['passenger_name'] = boleto_a_procesar.nombre_pasajero_procesado
                     datos_dict['NOMBRE_DEL_PASAJERO'] = boleto_a_procesar.nombre_pasajero_procesado
                     datos_dict['SOLO_NOMBRE_PASAJERO'] = boleto_a_procesar.nombre_pasajero_procesado
                     logger.info(f"💉 Inyectando Nombre manual '{boleto_a_procesar.nombre_pasajero_procesado}' al dataset.")
                # -----------------------------------------------------

                resultado_individual = self._procesar_ticket_individual(boleto_a_procesar, datos_dict, texto_completo, forced_client_id=forced_client_id)
                if resultado_individual:
                    resultados.append(resultado_individual)

            if resultados:
                logger.info(f"✅ Procesamiento completado. {len(resultados)} boletos generados.")
                # Si hay resultados con 'status'='REVIEW_REQUIRED', priorizamos devolver eso para iniciar el flujo de revisión
                for res in resultados:
                    if isinstance(res, dict) and res.get('status') == 'REVIEW_REQUIRED':
                        return res
                        
                return resultados[0] # Retornamos el primero si todos fueron éxitos (Ventas)
            
            return None

        except Exception as e:
            logger.error(f"💥 Error crítico en parser (procesar_boleto top-level): {e}", exc_info=True)
            if boleto:
                boleto.estado_parseo = 'ERR'
                # Log traceback snippet to DB
                import traceback
                tb = traceback.format_exc()[-300:]
                boleto.log_parseo = f"CRASH_TOP_LEVEL: {str(e)} | {tb}"
                boleto.save()
            return None

    def _procesar_ticket_individual(self, boleto, datos, texto_completo, forced_client_id=None):
        """Procesa un set de datos de UN ticket y actualiza el modelo BoletoImportado"""
        try:
            # SANITIZE FIRST: Normalize data to ensure JSON compatibility (dates -> strings)
            # This prevents TransactionManagementError in ALL code paths (including Missing ID interception)
            datos = self._sanitize_for_json(datos)
            
            logger.info(f"👉 Iniciando processed_ticket_individual para Boleto {boleto.pk}")
            with transaction.atomic():
                # Guardado/Actualización de Venta
                logger.info("DEBUG: Llamando a _guardar_venta_acumulativa...")
                venta = self._guardar_venta_acumulativa(boleto, datos, forced_client_id=forced_client_id)
                logger.info(f"DEBUG: Venta obtenida: {type(venta)}")
                
                if venta:
                    # Actualizar campos del modelo BoletoImportado PRIMERO
                    logger.info("DEBUG: Llamando a _actualizar_campos_modelo...")
                    self._actualizar_campos_modelo(boleto, datos)

                    # Generación de PDF Unificado
                    logger.info("DEBUG: Llamando a _generar_y_guardar_pdf...")
                    # 🚀 DE-DUPLICATION V2: Set placeholder 'SENDING' to block signals BEFORE generating PDF
                    # because generating/saving PDF triggers post_save.
                    try:
                        boleto.telegram_file_id = 'SENDING'
                        self._generar_y_guardar_pdf(boleto, datos)
                    finally:
                        # Ensure we don't leave it as 'SENDING' if it wasn't replaced by a real file_id
                        if boleto.telegram_file_id == 'SENDING':
                            boleto.telegram_file_id = None
                    
                    # 4. Gestión de Versionado (Detectar Re-emisiones)
                    logger.info("DEBUG: Llamando a _gestionar_versionado...")
                    self._gestionar_versionado(boleto)
                    
                    # --- INTERCEPCIÓN MANUAL (Feature: Missing IDs) ---
                    d = datos if isinstance(datos, dict) else {}
                    foid = d.get('passenger_document') or d.get('CODIGO_IDENTIFICACION') or boleto.foid_pasajero
                    
                    if not foid or foid == 'PENDIENTE' or str(foid).strip() == '':
                        logger.info(f"⚠️ INTERCEPCION: Foid faltante para Boleto {boleto.pk}")
                        boleto.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                        boleto.log_parseo = "Falta documento de identidad. Esperando input manual."
                        boleto.datos_parseados = datos 
                        boleto.save()
                        return {"status": "REVIEW_REQUIRED", "boleto_id": boleto.pk}
                    # --------------------------------------------------

                    boleto.estado_parseo = 'COM'
                    if hasattr(venta, 'pk'):
                        boleto.log_parseo = f"Parseo completado. Venta: {venta.pk}"
                    else:
                        boleto.log_parseo = f"Parseo completado. Venta (sin pk): {venta}"
                        
                    boleto.datos_parseados = datos
                    boleto.save()
                    return venta
            return None
        except Exception as e:
            # Emergency Error Handling
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Error procesando item individual: {e}\n{tb}", exc_info=True)
            try:
                # Try to save error to DB
                # REFRESH instance to avoid saving dirty fields (like invalid FKs from rolled back transaction)
                boleto.refresh_from_db()
                boleto.estado_parseo = 'ERR'
                boleto.log_parseo = f"CRASH_INDIVIDUAL: {e} | TB: {tb[-1500:]}" 
                boleto.save()
            except Exception as db_err:
                # If TransactionManagementError or other DB error, just log to console
                logger.critical(f"FATAL: No se pudo guardar el error en DB para Boleto {boleto.pk}. Motivo: {db_err}")
            return None

    def _sanitize_for_json(self, data):
        """Recursively converts dates/datetimes to strings for JSON serialization"""
        import datetime
        if isinstance(data, dict):
            return {k: self._sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(v) for v in data]
        elif isinstance(data, (datetime.date, datetime.datetime)):
            return data.isoformat()
        elif isinstance(data, Decimal):
             return str(data)
        return data

    def _safe_truncate(self, value, max_len):
        """Blindaje de Base de Datos: Trunca el valor al l\u00edmite del campo"""
        if value is None: return None
        s_val = str(value).strip()
        if len(s_val) > max_len:
            logger.warning(f"\u2702\ufe0f Truncando campo de {len(s_val)} a {max_len} caracteres. Valor original: {s_val!r}")
            return s_val[:max_len]
        return s_val


            


    def _actualizar_campos_modelo(self, boleto, datos):
        """Mapea los datos del diccionario a los campos del modelo BoletoImportado"""
        try:
            d = datos if isinstance(datos, dict) else {}
            
            # Formato Detectado (Mapeo Inteligente a Choices del Modelo)
            source = d.get('SOURCE_SYSTEM', '').upper()
            filename = boleto.archivo_boleto.name if boleto.archivo_boleto else ""
            ext = os.path.splitext(filename)[1].lower()
            
            # Mapeo de Negocio: Vincula la fuente detectada por el parser con el tipo de archivo
            mapping = {
                ('KIU', '.pdf'): 'PDF_KIU',
                ('KIU', '.eml'): 'EML_KIU',
                ('KIU', '.txt'): 'TXT_KIU',
                ('SABRE', '.pdf'): 'PDF_SAB',
                ('SABRE', '.eml'): 'EML_GEN',
                ('SABRE', '.txt'): 'TXT_SAB',
                ('AMADEUS', '.pdf'): 'PDF_AMA',
                ('AMADEUS', '.txt'): 'TXT_AMA',
            }
            
            formato_final = mapping.get((source, ext))
            if formato_final:
                boleto.formato_detectado = formato_final
            elif source in [c[0] for c in boleto.FormatoDetectado.choices]:
                # Si el parser ya devolvió un choice exacto (ej: 'PDF_KIU'), lo usamos directamente
                boleto.formato_detectado = source
            else:
                # Fallback genérico por extensión si no hay SOURCE_SYSTEM claro
                if ext == '.eml': boleto.formato_detectado = 'EML_GEN'
                else: boleto.formato_detectado = 'OTR'
            
            # Mapeos con Blindaje (Deep-Integrity)
            boleto.localizador_pnr = self._safe_truncate(
                d.get('pnr') or d.get('CODIGO_RESERVA') or d.get('localizador'), 20
            )

            boleto.numero_boleto = self._safe_truncate(
                d.get('ticket_number') or d.get('NUMERO_DE_BOLETO') or d.get('numero_boleto'), 50
            )
            
            # Nombre Pasajero
            p_name = d.get('passenger_name') or d.get('NOMBRE_DEL_PASAJERO') or d.get('nombre_completo')
            if not p_name and isinstance(d.get('pasajero'), dict):
                p_name = d.get('pasajero').get('nombre_completo')
            
            boleto.nombre_pasajero_completo = self._safe_truncate(p_name, 150)
            boleto.nombre_pasajero_procesado = self._safe_truncate(
                d.get('SOLO_NOMBRE_PASAJERO') or p_name, 150
            )
            
            boleto.aerolinea_emisora = self._safe_truncate(d.get('NOMBRE_AEROLINEA') or d.get('issuing_airline'), 150)
            boleto.direccion_aerolinea = d.get('DIRECCION_AEROLINEA') or d.get('issuing_agent', {}).get('address')
            boleto.agente_emisor = self._safe_truncate(d.get('AGENTE_EMISOR') or d.get('issuing_agent', {}).get('name'), 150)
            boleto.foid_pasajero = self._safe_truncate(
                d.get('passenger_document') or d.get('CODIGO_IDENTIFICACION'), 50
            )

            
            # Montos
            # Prioridad 1: Tarifas estructuradas
            tarifas = d.get('tarifas') or {}
            
            # TOTAL
            total_str = tarifas.get('total_amount')
            if not total_str:
                total_str = d.get('total_amount') or d.get('TOTAL') or d.get('total') or d.get('TOTAL_IMPORTE') or "0.00"
            
            logger.info(f"💰 [DEBUG] Extrayendo total_boleto. Raw: '{total_str}'")

            try:
                cleaned_str = str(total_str).upper().replace('USD', '').replace('EUR', '').replace('BS', '').strip()
                import re
                match = re.search(r'[\d,.]+', cleaned_str)
                if match:
                    cleaned_str = match.group(0).replace(',', '.') if ',' in cleaned_str and '.' not in cleaned_str else match.group(0).replace(',', '')
                    boleto.total_boleto = Decimal(cleaned_str)
                    logger.info(f"💰 [DEBUG] total_boleto asignado: {boleto.total_boleto}")
                else:
                    boleto.total_boleto = Decimal("0.00")
                    logger.warning(f"⚠️ [DEBUG] No se encontró patrón numérico en '{cleaned_str}'")
            except Exception as e: 
                logger.error(f"❌ [DEBUG] Error convirtiendo total: {e}")
                pass

            # TARIFA BASE
            fare_str = tarifas.get('fare_amount')
            if not fare_str:
                 fare_str = d.get('fare_amount') or d.get('TARIFA_IMPORTE') or "0.00"

            try:
                cleaned_fare = str(fare_str).upper().replace('USD', '').replace('EUR', '').replace('BS', '').strip()
                match = re.search(r'[\d,.]+', cleaned_fare)
                if match:
                    cleaned_fare = match.group(0).replace(',', '.') if ',' in cleaned_fare and '.' not in cleaned_fare else match.group(0).replace(',', '')
                    boleto.tarifa_base = Decimal(cleaned_fare)
                else:
                    boleto.tarifa_base = Decimal("0.00")
            except: 
                pass
            
            # Impuestos (string plano por ahora)
            boleto.impuestos_descripcion = d.get('tax_details') or d.get('IMPUESTOS')
            if isinstance(boleto.impuestos_descripcion, dict):
                boleto.impuestos_descripcion = str(boleto.impuestos_descripcion)
            
            # --- IMPUESTOS DESGLOSADOS (ERP - Phase 3) ---
            desglose = d.get('impuestos_desglose') or {}
            
            try: boleto.iva_monto = Decimal(str(desglose.get('iva', 0)))
            except: boleto.iva_monto = Decimal("0.00")
            
            try: boleto.inatur_monto = Decimal(str(desglose.get('inatur', 0)))
            except: boleto.inatur_monto = Decimal("0.00")
            
            try: boleto.otros_impuestos_monto = Decimal(str(desglose.get('otros', 0)))
            except: boleto.otros_impuestos_monto = Decimal("0.00")
            
            # TODO: Lógica de vinculación de Proveedor vendrá en el siguiente paso
            # ---------------------------------------------

            # Fecha (Parsing básico)
            fecha_str = d.get('issue_date') or d.get('FECHA_DE_EMISION')
            # TODO: Implementar parser de fecha robusto si es necesario
            
            # Lógica de vinculación de Proveedor
            iata_code = d.get('agencia_iata') or d.get('agency_iata')
            # Intentar extraer IATA del vuelo si no vino explícito
            if not iata_code and boleto.aerolinea_emisora:
                 from core.models_catalogos import Aerolinea
                 aero_obj = Aerolinea.objects.filter(nombre__icontains=boleto.aerolinea_emisora).first()
                 if aero_obj:
                     iata_code = aero_obj.codigo_iata

            office_id = d.get('office_id') # Si lo tuviéramos
            
            proveedor_encontrado = self._buscar_proveedor_por_identificador(iata_code, office_id)
            if proveedor_encontrado:
                boleto.proveedor_emisor = proveedor_encontrado
            
            # --- VALIDACIÓN NUMÉRICA (Ultimate Parser) ---
            from core.airline_utils import validate_airline_numeric_code
            if boleto.numero_boleto and iata_code:
                es_valido = validate_airline_numeric_code(boleto.numero_boleto, iata_code)
                if not es_valido:
                    boleto.log_parseo = (boleto.log_parseo or "") + "\n⚠️ ADVERTENCIA: El número de boleto no coincide con el código IATA de la aerolínea."
            # Ruta / Itinerario
            boleto.ruta_vuelo = d.get('ItinerarioFinalLimpio') or d.get('itinerary') or d.get('ruta')
            # ---------------------------------------------
            
            boleto.save()
            logger.info(f"Campos del modelo BoletoImportado {boleto.pk} actualizados.")

        except Exception as e:
            logger.error(f"Error actualizando campos del modelo boleto: {e}")

    def _gestionar_versionado(self, boleto):
        """
        Detecta si el boleto es una nueva versión (Re-emisión) de uno existente.
        Si encuentra un duplicado de número de boleto, incrementa la versión.
        """
        if not boleto.numero_boleto:
            return

        try:
            # Buscar otros boletos con el mismo número, excluyendo el actual
            duplicados = BoletoImportado.objects.filter(
                numero_boleto=boleto.numero_boleto
            ).exclude(
                pk=boleto.pk
            ).order_by('-version', '-fecha_subida')

            ultimo_boleto = duplicados.first()

            if ultimo_boleto:
                logger.info(f"🔄 Versión detectada: Boleto {boleto.numero_boleto} ya existe (ID {ultimo_boleto.pk}, v{ultimo_boleto.version}).")
                
                # Logic: Is it exactly the same? (Hash check ideally, here we assume it's a re-upload or re-issue)
                # Increment version
                boleto.version = ultimo_boleto.version + 1
                boleto.boleto_padre = ultimo_boleto
                boleto.estado_emision = BoletoImportado.EstadoEmision.REEMISION
                
                # Optional: Mark previous as 'HISTORICO' if we had such status logic (not implemented yet)
                boleto.save()
                
        except Exception as e:
            logger.error(f"Error en gestión de versionado: {e}")

    def _buscar_proveedor_por_identificador(self, iata, office_id):
        """Busca un proveedor que tenga estos IDs en su JSON `identificadores_gds`."""
        if not iata and not office_id:
            return None
            
        try:
            from core.models_catalogos import Proveedor
            # Opción 1: Búsqueda bruta (menos eficiente pero flexible para JSON)
             # TODO: Optimizar con consulta JSON exacta de DB si es Postgres, 
            # pero para SQLite/General iteramos o usamos contains.
            
            # Buscamos proveedores que sean CONSOLIDADOR o AEROLINEA/GDS
            candidatos = Proveedor.objects.filter(Q(identificadores_gds__isnull=False))
            
            for prov in candidatos:
                gds_ids = prov.identificadores_gds
                if not isinstance(gds_ids, dict): continue
                
                # Check IATA
                if iata:
                    iatas = gds_ids.get('IATA', [])
                    if isinstance(iatas, list) and iata in iatas:
                        return prov
                
                # Check Office ID (simplificado)
                if office_id:
                    offices = gds_ids.get('OFFICE_ID', [])
                    if isinstance(offices, list) and office_id in offices:
                        return prov
                        
            return None
        except Exception as e:
            logger.error(f"Error buscando proveedor: {e}")
            return None

    def _extraer_texto(self, boleto):
        """Extrae texto de PDF, EML o TXT"""
        try:
            archivo_origen = self._obtener_archivo_abierto(boleto)
            nombre_archivo = boleto.archivo_boleto.name.lower()
            
            if nombre_archivo.endswith('.pdf'):
                texto_extraido = ""
                with pdfplumber.open(archivo_origen) as pdf:
                    for page in pdf.pages:
                        try:
                            text = page.extract_text()
                            if text:
                                texto_extraido += text + "\n"
                        except Exception as e:
                            logger.warning(f"Error extrayendo página de PDF con pdfplumber: {e}")
                            continue
                
                # FALLBACK / COMPLEMENTO: pypdf
                # Algunos PDFs (Sabre) producen basura con pdfplumber en ciertas secciones (Equipaje).
                # Agregamos la extracción de pypdf al final para dar una segunda oportunidad a los regex.
                texto_pypdf = ""
                try:
                    reader = None
                    if pypdf:
                        reader = pypdf.PdfReader(archivo_origen)
                    elif PyPDF2:
                        reader = PyPDF2.PdfReader(archivo_origen)
                    
                    if reader:
                        archivo_origen.seek(0) # Reset pointer
                        for page in reader.pages:
                            texto_pypdf += (page.extract_text() or "") + "\n"
                        
                        if texto_pypdf:
                            texto_extraido += "\n\n--- FALLBACK EXTRACTION ---\n\n" + texto_pypdf
                except Exception as e_pypdf:
                    logger.warning(f"Fallback pypdf falló: {e_pypdf}")

                return texto_extraido
            
            elif nombre_archivo.endswith('.eml'):
                msg = BytesParser(policy=policy.default).parse(archivo_origen)
                
                # 🔒 INCLUIR HEADERS (CRÍTICO PARA DETECCIÓN: Accelya, Record Locator en Subject, etc)
                # DO NOT REMOVE THIS BLOCK. COPA PARSER DEPENDS ON IT.
                texto_final = "--- HEADERS START ---\n"
                if hasattr(msg, 'items'):
                    for k, v in msg.items():
                        texto_final += f"{k}: {v}\n"
                else:
                    logger.warning(f"EML Parser devolvió un objeto sin items(): {type(msg)}")
                texto_final += "--- HEADERS END ---\n\n"
                
                html_found = False
                
                # Estrategia: Buscar texto y HTML. Preferimos HTML para parsers web.
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        try:
                            # Prioridad HTML: Si encontramos HTML, lo usamos como fuente principal
                            # porque contiene la estructura (IDs, tablas) que WebReceiptParser necesita.
                            if ctype == 'text/html':
                                content = part.get_content()
                                if content:
                                    # 🔒 CRITICAL: USE += (APPEND). DO NOT OVERWRITE (=) OR HEADERS WILL BE LOST.
                                    texto_final += content
                                    html_found = True
                                    break # Encontramos HTML, nos detenemos.
                            
                            # Si no es HTML, guardamos text/plain por si acaso no hay HTML
                            elif ctype == 'text/plain' and not html_found:
                                content = part.get_content()
                                if content:
                                    # 🔒 CRITICAL: USE += (APPEND). DO NOT OVERWRITE (=) OR HEADERS WILL BE LOST.
                                    texto_final += content
                        except Exception:
                            pass
                else:
                    texto_final += msg.get_content()
                
                return texto_final
                    
            else: # TXT o Fallback
                content = archivo_origen.read()
                return content.decode('utf-8', errors='ignore')

        except Exception as e:
            logger.error(f"Error extrayendo texto: {e}")
            return None

    def _obtener_archivo_abierto(self, boleto):
        """Devuelve un objeto file-like abierto (BytesIO o FieldFile opened)."""
        if hasattr(boleto.archivo_boleto, 'url') and boleto.archivo_boleto.url.startswith('http'):
            try:
                response = requests.get(boleto.archivo_boleto.url, timeout=15)
                response.raise_for_status()
                return BytesIO(response.content)
            except Exception as e:
                logger.error(f"Error descargando boleto remoto: {e}")
                # Fallback por si acaso es local pero tiene URL mal formada o no accesible
                pass
        
        # Para archivos locales o almacenamiento directo
        f = boleto.archivo_boleto.open('rb')
        f.seek(0)
        return f

    def _guardar_venta_acumulativa(self, boleto, datos, forced_client_id=None):
        agencia = boleto.agencia or Agencia.objects.first()
        # Normalización de datos para evitar errores de clave
        # Soportamos tanto estilo diccionario como estilo objeto si viniera así
        d = datos if isinstance(datos, dict) else (datos.to_dict() if hasattr(datos, 'to_dict') else {})
        
        # Extracción segura de datos clave con blindaje
        pnr = self._safe_truncate(
            d.get('pnr') or d.get('CODIGO_RESERVA') or d.get('localizador') or "SIN-PNR", 20
        )

        
        pasajero_raw = d.get('passenger_name') or d.get('NOMBRE_DEL_PASAJERO') or d.get('pasajero', "PASAJERO DESCONOCIDO")
        if isinstance(pasajero_raw, dict): pasajero_raw = pasajero_raw.get('nombre_completo', 'DESCONOCIDO')
        
        # Blindaje 2: Limitar nombre para el modelo Cliente (max_length=100)
        pasajero_raw = self._safe_truncate(pasajero_raw, 100)

        
        # Cliente
        nombre_search = pasajero_raw.split('/')[0] if '/' in pasajero_raw else pasajero_raw
        
        # 1. Intentar buscar por nombre
        cliente = Cliente.objects.filter(nombres__icontains=nombre_search).first()
        
        if forced_client_id:
            try:
                cliente = Cliente.objects.get(id=forced_client_id)
                logger.info(f"📍 Usando cliente forzado ID {forced_client_id}: {cliente}")
            except Cliente.DoesNotExist:
                logger.warning(f"⚠️ Cliente forzado ID {forced_client_id} no encontrado.")
                cliente = None
        
        if not cliente:
            # 2. Si no existe, crear uno nuevo con email ÚNICO para evitar IntegrityError
            import uuid
            unique_email = f"cliente_{uuid.uuid4().hex[:8]}@sin-email.com"
            cliente = Cliente.objects.create(
                nombres=pasajero_raw,
                apellidos='.',
                email=unique_email
            )
        
        # Moneda
        cod_moneda = d.get('moneda') or d.get('TOTAL_MONEDA') or 'USD'
        moneda, _ = Moneda.objects.get_or_create(codigo_iso=cod_moneda, defaults={'nombre': cod_moneda})
        
        # Montos
        # Montos
        # Prioridad 1: Buscar en estructura estructurada 'tarifas' si existe
        tarifas = d.get('tarifas') or {}
        total_str = tarifas.get('total_amount')
        
        # Prioridad 2: Buscar en claves legacy top-level
        if not total_str:
             total_str = d.get('total') or d.get('total_amount') or d.get('TOTAL_IMPORTE') or "0.00"
        
        try: 
            # Limpiar string de moneda (USD, EUR, etc) y caracteres no numéricos excepto . y ,
            cleaned_str = str(total_str).upper().replace('USD', '').replace('EUR', '').replace('BS', '').strip()
            # Si tiene coma como decimal, reemplazar (asumiendo formato estándar si no es miles)
            # Mejor dejar que el limpieza propia ocurra o usar regex
            import re
            match = re.search(r'[\d,.]+', cleaned_str)
            if match:
                cleaned_str = match.group(0).replace(',', '.') if ',' in cleaned_str and '.' not in cleaned_str else match.group(0).replace(',', '')
                total_val = Decimal(cleaned_str)
            else:
                total_val = Decimal("0.00")
        except: 
            total_val = Decimal("0.00")

        # Venta
        venta, created = Venta.objects.get_or_create(
            localizador=pnr,
            defaults={
                'agencia': agencia, 
                'cliente': cliente, 
                'moneda': moneda, 
                'total_venta': 0, 
                'estado': 'PEN', 
                'fecha_venta': timezone.now()
            }
        )
        
        # --- AUTO-HEALING ORPHANED VENTAS ---
        if not created:
             try:
                 # Check if the relation is valid
                 # Explicitly check for None
                 if venta.cliente_id is None: 
                      venta.cliente_id = cliente.pk
                      venta.save(update_fields=['cliente'])
                      logger.warning(f"🩹 Venta {venta.pk} huérfana (None) reparada (Cliente ID asignado: {cliente.pk})")
             except Exception as e_orphan:
                 # Catching EVERYTHING and using ID assignment to bypass "instance must be X" errors
                 logger.warning(f"🩹 Venta {venta.pk} referencia rota. Reparando con ID {cliente.pk} (Error original: {e_orphan})...")
                 venta.cliente_id = cliente.pk
                 venta.save(update_fields=['cliente'])
        # ------------------------------------

        # Item Venta
        # TICKET NUMBER (Identificador Único Real)
        ticket_number = d.get('ticket_number') or d.get('NUMERO_DE_BOLETO') or d.get('numero_boleto')
        
        # Item Venta (Idempotente)
        producto = ProductoServicio.objects.filter(tipo_producto='AIR').first() or ProductoServicio.objects.first()
        
        # Estrategia de búsqueda de duplicados:
        # 1. Por Número de Boleto (Lo más preciso, distingue homónimos)
        item_existente = None
        if ticket_number:
            item_existente = ItemVenta.objects.filter(
                venta=venta,
                descripcion_personalizada__icontains=str(ticket_number)
            ).first()
        
        # 2. Fallback: Por PNR + Nombre (Si no hay ticket number, riesgo de homónimos pero mejor que nada)
        if not item_existente:
             item_existente = ItemVenta.objects.filter(
                venta=venta,
                descripcion_personalizada__icontains=pnr
            ).filter(
                descripcion_personalizada__icontains=pasajero_raw
            ).first()

        # Descripción única incluyendo el ticket number si existe
        descripcion_final = f"Boleto {ticket_number} - {pnr} ({pasajero_raw})" if ticket_number else f"Boleto - {pnr} ({pasajero_raw})"

        if item_existente:
             # Actualizar existente
             item_existente.descripcion_personalizada = descripcion_final # Actualizar desc si cambió
             item_existente.cantidad = 1
             item_existente.total_item_venta = total_val
             item_existente.precio_unitario_venta = total_val
             item_existente.costo_neto_proveedor = total_val * Decimal("0.90")
             item_existente.comision_agencia_monto = total_val * Decimal("0.10")
             item_existente.save()
        else:
            # Crear nuevo
            ItemVenta.objects.create(
                venta=venta,
                producto_servicio=producto,
                descripcion_personalizada=descripcion_final,
                cantidad=1, 
                total_item_venta=total_val, 
                precio_unitario_venta=total_val, 
                costo_neto_proveedor=total_val * Decimal("0.90"), 
                comision_agencia_monto=total_val * Decimal("0.10"), 
                impuestos_item_venta=0, 
                codigo_reserva_proveedor=pnr
            )

        # Recalcular Total Venta
        total_real = ItemVenta.objects.filter(venta=venta).aggregate(Sum('total_item_venta'))['total_item_venta__sum'] or 0
        venta.total_venta = total_real
        venta.save()
        
        boleto.venta_asociada = venta
        boleto.save()
        return venta

    def _generar_y_guardar_pdf(self, boleto, datos):
        """Genera el PDF usando la plantilla correcta y lo guarda en el modelo."""
        try:
            from django.core.files.base import ContentFile
            pdf_bytes, filename = generate_ticket(datos)
            
            if pdf_bytes:
                # Usar save=False para evitar disparo de señales prematuro (ya se guardará en _procesar_ticket_individual)
                boleto.archivo_pdf_generado.save(
                    f"Boleto_{boleto.pk}_{filename}.pdf",
                    ContentFile(pdf_bytes),
                    save=False
                )
                boleto.save(update_fields=['archivo_pdf_generado']) # Guardar solo este campo para persistir archivo
                logger.info(f"✅ PDF Generado y guardado para boleto {boleto.pk}")

                # --- NOTIFICACIÓN TELEGRAM AUTOMÁTICA ---
                if boleto.telegram_file_id:
                     logger.info(f"🔕 Notificación Telegram omitida: Ya existe file_id ({boleto.telegram_file_id})")
                     return
                try:
                    from core.services.telegram_notification_service import TelegramNotificationService
                    from django.conf import settings
                    
                    moneda_simbolo = 'USD'
                    try:
                        if boleto.datos_parseados:
                            data = boleto.datos_parseados.get('normalized', boleto.datos_parseados)
                            moneda_simbolo = data.get('total_currency') or data.get('TOTAL_MONEDA') or 'USD'
                    except:
                        pass

                    caption = (
                        f"🎫 <b>Nuevo Boleto Procesado ({boleto.formato_detectado})</b>\n"
                        f"🆔 ID: {boleto.pk}\n"
                        f"✈️ PNR: {boleto.localizador_pnr}\n"
                        f"👤 Pasajero: {boleto.nombre_pasajero_completo}\n"
                        f"💰 Total: {boleto.total_boleto} {moneda_simbolo}"
                    )
                    
                    pdf_file_input = None
                    try:
                        # Intento 1: Path local (FileSystemStorage)
                        if hasattr(boleto.archivo_pdf_generado, 'path'):
                            pdf_file_input = boleto.archivo_pdf_generado.path
                    except NotImplementedError:
                         # Intento 2: URL (Cloudinary/S3)
                         if hasattr(boleto.archivo_pdf_generado, 'url'):
                             pdf_file_input = boleto.archivo_pdf_generado.url

                    if pdf_file_input:
                        # 1. ENVIAR A STORAGE (Canal DB)
                        # Usamos explícitamente el canal de almacenamiento si está definido
                        storage_id = getattr(settings, 'TELEGRAM_STORAGE_CHANNEL_ID', None)
                        # SaaS Logic: Usar storage channel de la agencia si existe
                        if boleto.agencia and boleto.agencia.configuracion_api.get('TELEGRAM_STORAGE_CHANNEL_ID'):
                            storage_id = boleto.agencia.configuracion_api.get('TELEGRAM_STORAGE_CHANNEL_ID')

                        file_id_generado = None
                        
                        if storage_id:
                             # Enviar SOLO al canal de storage para obtener un ID permanente
                             logger.info(f"📤 Enviando a Storage Channel ({storage_id})...")
                             file_id_generado = TelegramNotificationService.send_document(
                                 file_path=pdf_file_input,
                                 chat_id=storage_id,
                                 caption=f"Storage: {boleto.localizador_pnr}",
                                 agencia=boleto.agencia
                             )
                        if file_id_generado and isinstance(file_id_generado, str):
                            boleto.telegram_file_id = file_id_generado
                            boleto.save(update_fields=['telegram_file_id'])
                            logger.info(f"💾 Telegram File ID guardado: {file_id_generado}")

                        # 2. ENVIAR A GRUPO GENERAL (Notificación)
                        group_id = getattr(settings, 'TELEGRAM_GROUP_ID', None)
                        if group_id and group_id != storage_id:
                            logger.info(f"🔔 Enviando notificación a Grupo: {group_id}")
                            # Si tenemos file_id, usamos ese (más rápido), sino subimos el archivo de nuevo
                            path_or_id = file_id_generado if file_id_generado and isinstance(file_id_generado, str) else pdf_file_input
                            
                            TelegramNotificationService.send_document(
                                file_path=path_or_id,
                                caption=caption,
                                chat_id=group_id,
                                agencia=boleto.agencia
                            )
                        
                        # Si no se envió a storage pero sí llegamos aquí, limpiar el placeholder si falló el file_id
                        if boleto.telegram_file_id == 'SENDING' and not file_id_generado:
                            boleto.telegram_file_id = None
                            boleto.save(update_fields=['telegram_file_id'])
                    else:
                        logger.error(f"❌ No se pudo obtener Path ni URL del PDF para boleto {boleto.pk}")

                except Exception as e_tg:
                    logger.error(f"⚠️ Error enviando notificación Telegram en TicketParserService: {e_tg}")
                # ----------------------------------------

            else:
                logger.warning(f"⚠️ generate_ticket retornó vacío para boleto {boleto.pk}")
                
        except Exception as e:
            logger.error(f"❌ Error generando PDF para boleto {boleto.pk}: {e}")


# =========================================================
# FUNCIONES ORQUESTADORAS (PUENTES)
# =========================================================

def orquestar_parseo_de_boleto(archivo_subido):
    """
    Función orquestadora para vistas API. Recibe el archivo, extrae texto y parsea.
    ACTUALIZADO: Usa los nuevos parsers refactorizados (SabreParser, KIUParser, etc.)
    """
    logger.info(f"🚀 Iniciando orquestación de parseo (API) para: {archivo_subido.name}")
    
    try:
        # 1. Leer y extraer texto
        contenido = archivo_subido.read()
        archivo_subido.seek(0)
        
        nombre_archivo = archivo_subido.name.lower()
        texto_extraido = ""
        
        if nombre_archivo.endswith('.pdf'):
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(contenido)) as pdf:
                    for page in pdf.pages:
                        texto_extraido += (page.extract_text() or "") + "\n"
            except Exception as e:
                return None, f"Error leyendo PDF: {str(e)}"
        else:
            texto_extraido = contenido.decode('utf-8', errors='ignore')

        if not texto_extraido.strip():
            return None, "El archivo no contiene texto legible."

        # 2. Usar el motor de parseo universal centralizado
        from core.ticket_parser import extract_data_from_text
        
        path_pdf = None
        try:
            if hasattr(archivo_subido, 'temporary_file_path'):
                path_pdf = archivo_subido.temporary_file_path()
        except:
            pass

        parsed_data = extract_data_from_text(texto_extraido, pdf_path=path_pdf)
        
        if not parsed_data:
            logger.error("❌ El motor de parseo centralizado devolvió un resultado vacío.")
            return None, "Error: El motor de parseo no pudo extraer datos."

        if "error" in parsed_data:
             logger.error(f"❌ Error reportado por el motor de parseo: {parsed_data['error']}")
             return None, parsed_data["error"]

        # Normalización: Queremos devolver SIEMPRE una lista de diccionarios (Uno por ticket)
        resultados_lista = []

        # Caso 1: Retorno Dict (WebReceiptParser / Avior / AI Universal)
        if isinstance(parsed_data, dict):
             if parsed_data.get('is_multi_pax') and 'tickets' in parsed_data:
                 # Es un paquete de múltiples tickets
                 logger.info(f"📋 Multi-Pax detectado: {len(parsed_data['tickets'])} boletos")
                 resultados_lista = parsed_data['tickets']
             else:
                 # Es un solo ticket en formato dict
                 resultados_lista = [parsed_data]
        
        # Caso 2: Retorno Objeto ParsedTicketData (Legacy Parsers)
        elif hasattr(parsed_data, 'to_dict'):
            resultados_lista = [parsed_data.to_dict()]
        
        else:
            logger.warning(f"⚠️ Tipo de retorno desconocido: {type(parsed_data)}")
            resultados_lista = []

        # Validar si extrajo algo útil
        validos = []
        for datos in resultados_lista:
            # Relajamos validación: si tiene PNR o Número de boleto o Nombre es aceptable
            if datos.get('pnr') != 'No encontrado' or \
               datos.get('ticket_number') != 'No encontrado' or \
               datos.get('NUMERO_DE_BOLETO') or \
               datos.get('NOMBRE_DEL_PASAJERO'):
                 validos.append(datos)
        
        if validos:
            logger.info(f"✅ Parseo exitoso unificado. {len(validos)} tickets válidos.")
            return validos, "Parseo exitoso"
        else:
            logger.warning("⚠️ El motor unificado no extrajo datos mínimos válidos")
            return None, "No se pudieron extraer datos válidos del boleto"
        
        # Si ningún parser funcionó, retornar error
        logger.error("❌ Ningún parser pudo procesar el boleto")
        return None, "No se pudo identificar el formato del boleto"

    except Exception as e:
        logger.exception("Error en orquestar_parseo_de_boleto")
        return None, f"Excepción interna: {str(e)}"

def generar_pdf_en_memoria(datos, path_ignored=None):
    """
    Wrapper compatible para generar PDF desde datos parseados.
    Ignora 'path_ignored' porque generate_ticket decide la plantilla internamente.
    Returns: bytes del PDF
    """
    try:
        pdf_bytes, filename = generate_ticket(datos)
        return pdf_bytes
    except Exception as e:
        logger.error(f"Error en generar_pdf_en_memoria: {e}")
        return None
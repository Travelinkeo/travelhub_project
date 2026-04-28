# -*- coding: utf-8 -*-
# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# This service handles the core parsing logic, PDF generation, and Notifications.
# LOGIC IS LOCKED. DO NOT MODIFY WITHOUT EXPLICIT AUTHORIZATION.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------
import logging
import os
import io
import json
import requests
import pdfplumber
from email import policy
from email.parser import BytesParser
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from io import BytesIO
from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import transaction, OperationalError, IntegrityError
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
    from apps.crm.models import Cliente

try:
    from core.models_catalogos import ProductoServicio
except ImportError:
    from core.models import ProductoServicio

from core.models import Agencia, Moneda
from apps.bookings.models import BoletoImportado, Venta, ItemVenta
from core.ticket_parser import extract_data_from_text, generate_ticket
from core.services.parsers.pdf_generation import PdfGenerationService

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class TicketParserService:
    """
    🏢 MULTI-TENANT | 🧠 IA / GOD MODE | 🚨 CRÍTICO
    Servicio principal y Orquestador de lógica de negocio para el procesamiento de Boletos Importados.
    
    ¿Qué hace exactamente?
    Controla el flujo completo de vida de un boleto subido a la plataforma:
    1. Extracción de texto crudo (PDF, EML, TXT).
    2. Delega la interpretación del formato a parsers tradicionales o de IA (Gemini).
    3. Normaliza los datos a un formato JSON estándar.
    4. 🚨 Inserta/Actualiza datos en la base de datos financiera de forma atómica (Ventas, Ítems, Impuestos).
    5. Gestiona reintentos en bloqueos (Deadlocks) y emite notificaciones ASÍNCRONAS.
    """

    def procesar_boleto(self, boleto_id, forced_client_id=None, ignore_manual=False):
        """
        Punto de entrada principal para el pipeline de parsing de boletos.
        
        Args:
            boleto_id (int): PK del modelo BoletoImportado a procesar.
            forced_client_id (int, optional): ID asignación forzada al cliente de la factura, ignora auto-resolve.
            ignore_manual (bool, optional): Si True, ignora inyecciones de ID manuales (útil para IA Re-extracción completa).
            
        Returns:
            Venta | dict | None: Instancia de Venta activa, dict con status si necesita REVIEW_REQUIRED manual, o None en error total.
            
        Raises:
            OperationalError: Fallo de BD propagado tras intentos fallidos si hay deadlock persistente.
            Exception: Atrapa error crítico general para evitar cierre abrupto de Celery workers.
            
        # 🚨 CRÍTICO: Implementa reintentos (backoff loop) dado que si suben docenas de boletos a la vez (GDS Bulk), 
        # SQLite/Postgres podría arrojar "Database is locked" por colisiones de commit atómico en Venta.
        """
        import time
        max_retries = 3
        retry_delay = 1 # segundo
        
        for attempt in range(max_retries):
            try:
                return self._ejecutar_procesamiento_base(boleto_id, forced_client_id, ignore_manual=ignore_manual)
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

    def _ejecutar_procesamiento_base(self, boleto_id, forced_client_id=None, ignore_manual=False):
        boleto = None
        try:
            boleto = BoletoImportado.all_objects.get(pk=boleto_id)
            logger.info(f"🔄 Procesando boleto ID {boleto_id} (ignore_manual={ignore_manual})")

            # Reset log al inicio
            boleto.log_parseo = "Iniciando re-procesamiento..."
            boleto.save(update_fields=['log_parseo'])

            # 1. Extracción de Texto
            texto_completo = self._extraer_texto(boleto)
            
            if not texto_completo:
                error_msg = "❌ Archivo vacío o formato no soportado."
                logger.error(error_msg)
                boleto.estado_parseo = 'ERR'
                boleto.log_parseo = error_msg
                boleto.save()
                return None

            # 2. Parseo
            path_pdf = None
            try:
                if hasattr(boleto.archivo_boleto, 'path'):
                    path_pdf = boleto.archivo_boleto.path
            except: pass
                 
            try:
                datos = extract_data_from_text(texto_completo, pdf_path=path_pdf)
            except Exception as e_p:
                logger.error(f"Error en extract_data_from_text: {e_p}")
                datos = {"error": f"Fallo en parser primario: {str(e_p)}"}

            # Fallback IA
            if datos is None or (isinstance(datos, dict) and "error" in datos):
                logger.warning("⚠️ Activando Salvavidas IA...")
                try:
                    from core.parsers.ai_universal_parser import UniversalAIParser
                    datos = UniversalAIParser().parse(texto_completo, pdf_path=path_pdf)
                except Exception as e_ai:
                    logger.error(f"❌ Salvavidas IA falló: {e_ai}")
                    datos = {"error": f"Error IA: {str(e_ai)}"}

            if isinstance(datos, dict) and "error" in datos:
                boleto.estado_parseo = 'ERR'
                boleto.log_parseo = datos['error']
                boleto.save()
                return None

            # ... rest of the logic ...

            # 3. Procesamiento Multi-Pax vs Single
            lista_tickets = []
            if isinstance(datos, dict) and datos.get('boletos'):
                lista_tickets = datos.get('boletos', [])
            elif isinstance(datos, dict) and datos.get('is_multi_pax'):
                lista_tickets = datos.get('tickets', [])
            elif isinstance(datos, list):
                lista_tickets = datos
            else:
                lista_tickets = [datos]

            resultados = []
            logger.info(f"📋 Se detectaron {len(lista_tickets)} boletos en el archivo.")

            for i, info_ticket in enumerate(lista_tickets):
                boleto_a_procesar = boleto
                if len(lista_tickets) > 1 and i > 0:
                    hermanos = BoletoImportado.objects.filter(
                        archivo_boleto=boleto.archivo_boleto
                    ).exclude(pk=boleto.pk).order_by('pk')
                    
                    indice_hermano = i - 1
                    if indice_hermano < len(hermanos):
                        boleto_a_procesar = hermanos[indice_hermano]
                        logger.info(f"♻️ Reutilizando hermano existente ID {boleto_a_procesar.pk} para ticket {i}")
                    else:
                        boleto_a_procesar = BoletoImportado.objects.create(
                            archivo_boleto=boleto.archivo_boleto,
                            estado_parseo='PRO' 
                        )
                        logger.info(f"✨ Creando nuevo hermano para ticket {i}")
                
                datos_dict = info_ticket
                if hasattr(info_ticket, 'to_dict'):
                    datos_dict = info_ticket.to_dict()
                
                # --- ALIAS INYECTION FOR COMPATIBILITY ---
                # Evita que el engine financiero y el ticket parser no detecten las llaves estandarizadas
                if 'codigo_reserva' in datos_dict: datos_dict['CODIGO_RESERVA'] = datos_dict['codigo_reserva']
                if 'nombre_pasajero' in datos_dict: datos_dict['NOMBRE_DEL_PASAJERO'] = datos_dict['nombre_pasajero']
                if 'solo_nombre_pasajero' in datos_dict: datos_dict['SOLO_NOMBRE_PASAJERO'] = datos_dict['solo_nombre_pasajero']
                if 'numero_boleto' in datos_dict: datos_dict['NUMERO_DE_BOLETO'] = datos_dict['numero_boleto']
                if 'fecha_emision' in datos_dict: datos_dict['FECHA_DE_EMISION'] = datos_dict['fecha_emision']
                if 'nombre_aerolinea' in datos_dict: datos_dict['NOMBRE_AEROLINEA'] = datos_dict['nombre_aerolinea']
                if 'codigo_identificacion' in datos_dict: datos_dict['CODIGO_IDENTIFICACION'] = datos_dict['codigo_identificacion']
                if 'tarifa' in datos_dict: datos_dict['fare_amount'] = datos_dict['tarifa']
                if 'impuestos' in datos_dict: datos_dict['taxes_amount'] = datos_dict['impuestos']
                if 'total' in datos_dict: datos_dict['total_amount'] = datos_dict['total']
                if 'moneda' in datos_dict: datos_dict['TOTAL_MONEDA'] = datos_dict['moneda']
                if 'itinerario' in datos_dict:
                    # Garantizar compatibilidad con iteraciones downstream
                    datos_dict['ItinerarioFinalLimpio'] = json.dumps(datos_dict['itinerario'])
                    try:
                        # Si es posible, convertir la lista de tramos en el formato tradicional
                         segmentos = []
                         for tramo in datos_dict['itinerario']:
                              if isinstance(tramo, dict):
                                   segmento = {
                                        'aerolinea': tramo.get('aerolinea'),
                                        'vuelo': tramo.get('numero_vuelo'),
                                        'origen': tramo.get('origen'),
                                        'fecha_salida': tramo.get('fecha_salida'),
                                        'hora_salida': tramo.get('hora_salida'),
                                        'destino': tramo.get('destino'),
                                        'hora_llegada': tramo.get('hora_llegada'),
                                        'fecha_llegada': tramo.get('fecha_llegada'),
                                        'clase': tramo.get('clase') or tramo.get('cabina'),
                                        'localizador_aerolinea': tramo.get('localizador_aerolinea')
                                   }
                                   segmentos.append(segmento)
                         datos_dict['segmentos'] = segmentos
                    except Exception as alias_err:
                         logger.warning(f"Error generando alias de segmentos: {alias_err}")
                
                # --- INYECCIÓN DE DATOS MANUALES ---
                if not ignore_manual:
                    if boleto_a_procesar.foid_pasajero and boleto_a_procesar.foid_pasajero != 'None':
                         datos_dict['passenger_document'] = boleto_a_procesar.foid_pasajero
                         datos_dict['CODIGO_IDENTIFICACION'] = boleto_a_procesar.foid_pasajero
                         logger.info(f"💉 Inyectando FOID manual '{boleto_a_procesar.foid_pasajero}' al dataset.")

                    if boleto_a_procesar.nombre_pasajero_procesado and boleto_a_procesar.nombre_pasajero_procesado != 'None':
                         datos_dict['passenger_name'] = boleto_a_procesar.nombre_pasajero_procesado
                         datos_dict['NOMBRE_DEL_PASAJERO'] = boleto_a_procesar.nombre_pasajero_procesado
                         datos_dict['SOLO_NOMBRE_PASAJERO'] = boleto_a_procesar.nombre_pasajero_procesado
                         logger.info(f"💉 Inyectando Nombre manual '{boleto_a_procesar.nombre_pasajero_procesado}' al dataset.")
                else:
                    logger.info("🚫 AI OVERRIDE: Omitiendo inyección de datos manuales para limpieza profunda.")

                resultado_individual = self._procesar_ticket_individual(boleto_a_procesar, datos_dict, texto_completo, forced_client_id=forced_client_id)
                if resultado_individual:
                    resultados.append(resultado_individual)

            if resultados:
                logger.info(f"✅ Procesamiento completado. {len(resultados)} boletos generados.")
                for res in resultados:
                    if isinstance(res, dict) and res.get('status') == 'REVIEW_REQUIRED':
                        return res
                return resultados[0]
            
            return None

        except Exception as e:
            logger.error(f"💥 Error crítico en parser (procesar_boleto top-level): {e}", exc_info=True)
            if boleto:
                boleto.estado_parseo = 'ERR'
                import traceback
                tb = traceback.format_exc()[-300:]
                boleto.log_parseo = f"CRASH_TOP_LEVEL: {str(e)} | {tb}"
                boleto.save()
            return None

    def _procesar_ticket_individual(self, boleto, datos, texto_completo, forced_client_id=None):
        """
        Sub-orquestador en el bucle que gestiona un boleto_id específico. Afecta directamente DB (Venta, Ítems, PDF).
        
        Args:
            boleto (BoletoImportado): Instancia persistida del ticket en la DB.
            datos (dict): JSON devuelto por parseadores (Gemini o Regex) ya extraído.
            texto_completo (str): Texto en crudo por si se requiere retro-búsqueda temporal.
            forced_client_id (int, optional): Asignación forzada manual del dev (HTMX front).
            
        Returns:
            Venta | dict | None: Venta creada/vinculada o un dicccionario '{status: REVIEW}' si se detecta IA Confidence < 70%.
        """
        try:
            datos = self._sanitize_for_json(datos)
            
            logger.info(f"👉 Iniciando processed_ticket_individual para Boleto {boleto.pk}")
            # 🚨 CRÍTICO: Bloque Atómico. Modificará Venta, ItemVenta, y ComisionFreelancer en bloque.
            # Si el cálculo del parseo o PDF crashea en medio, todo hace Rollback. Esto mantiene consistencia fiscal.
            with transaction.atomic():
                logger.info("DEBUG: Llamando a _guardar_venta_acumulativa...")
                venta = self._guardar_venta_acumulativa(boleto, datos, forced_client_id=forced_client_id)
                logger.info(f"DEBUG: Venta obtenida: {type(venta)}")
                
                if venta:
                    logger.info("DEBUG: Llamando a _actualizar_campos_modelo...")
                    self._actualizar_campos_modelo(boleto, datos)

                    logger.info("DEBUG: Llamando a _generar_y_guardar_pdf...")
                    try:
                        boleto.telegram_file_id = 'SENDING'
                        self._generar_y_guardar_pdf(boleto, datos)
                    finally:
                        if boleto.telegram_file_id == 'SENDING':
                            boleto.telegram_file_id = None
                    
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
                    
                    # --- INTERCEPCIÓN POR BAJA CONFIANZA ---
                    confidence_val = d.get('confidence_score')
                    confidence = float(confidence_val) if confidence_val is not None else 1.0
                    if confidence < 0.7:
                        logger.info(f"⚠️ INTERCEPCION: Baja confianza ({confidence}) para Boleto {boleto.pk}")
                        boleto.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                        notas = d.get('notas_advertencia') or "Confianza baja en la extracción de datos."
                        boleto.log_parseo = f"Revisión requerida por baja confianza AI ({confidence}). Notas: {notas}"
                        boleto.datos_parseados = datos
                        boleto.save()
                        return {"status": "REVIEW_REQUIRED", "boleto_id": boleto.pk}

                    boleto.estado_parseo = 'COM'
                    if hasattr(venta, 'pk'):
                        boleto.log_parseo = f"Parseo completado. Venta: {venta.pk}"
                    else:
                        boleto.log_parseo = f"Parseo completado. Venta (sin pk): {venta}"
                        
                    boleto.datos_parseados = datos
                    boleto.save()

                    # 🚀 NOTIFICACION MAGIC TOAST (Celery/HTMX Polling)
                    try:
                        if hasattr(venta, 'creado_por') and venta.creado_por:
                             from core.models.notificaciones import NotificacionAgente
                             NotificacionAgente.objects.create(
                                 usuario=venta.creado_por,
                                 tipo='ai_magic',
                                 titulo='God Mode Completado ✨',
                                 mensaje=f"Gemini estructuró el PNR {venta.localizador} exitosamente.",
                                 icono='auto_awesome'
                             )
                    except Exception as e:
                        logger.warning(f"No se pudo crear la notificación Magic Toast (NotificacionAgente): {e}")

                    return venta
            return None
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Error procesando item individual: {e}\n{tb}", exc_info=True)
            try:
                boleto.refresh_from_db()
                boleto.estado_parseo = 'ERR'
                boleto.log_parseo = f"CRASH_INDIVIDUAL: {e} | TB: {tb[-1500:]}" 
                boleto.save()
            except Exception as db_err:
                logger.critical(f"FATAL: No se pudo guardar el error en DB para Boleto {boleto.pk}. Motivo: {db_err}")
            return None

    def _sanitize_for_json(self, data):
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
        if value is None: return None
        s_val = str(value).strip()
        if len(s_val) > max_len:
            logger.warning(f"✂️ Truncando campo de {len(s_val)} a {max_len} caracteres. Valor original: {s_val!r}")
            return s_val[:max_len]
        return s_val

    def _actualizar_campos_modelo(self, boleto, datos):
        try:
            d = datos if isinstance(datos, dict) else {}
            
            source = d.get('SOURCE_SYSTEM', '').upper()
            filename = boleto.archivo_boleto.name if boleto.archivo_boleto else ""
            ext = os.path.splitext(filename)[1].lower()
            
            mapping = {
                ('KIU', '.pdf'): 'PDF_KIU',
                ('KIU', '.eml'): 'EML_KIU',
                ('KIU', '.txt'): 'TXT_KIU',
                ('SABRE', '.pdf'): 'PDF_SAB',
                ('SABRE', '.eml'): 'EML_GEN',
                ('SABRE', '.txt'): 'TXT_SAB',
                ('AMADEUS', '.pdf'): 'PDF_AMA',
                ('AMADEUS', '.txt'): 'TXT_AMA',
                ('AI_KIU', '.pdf'): 'PDF_KIU',
                ('AI_KIU', '.eml'): 'EML_KIU',
                ('AI_KIU', '.txt'): 'TXT_KIU',
                ('AI_SABRE', '.pdf'): 'PDF_SAB',
                ('AI_SABRE', '.txt'): 'TXT_SAB',
                ('COPA_SPRK', '.eml'): 'EML_GEN',
                ('AI_COPA', '.eml'): 'EML_GEN',
            }
            
            formato_final = mapping.get((source, ext))
            
            if not formato_final:
                if 'SABRE' in source:
                    formato_final = 'PDF_SAB' if ext == '.pdf' else 'TXT_SAB'
                elif 'KIU' in source:
                    formato_final = 'PDF_KIU' if ext == '.pdf' else 'TXT_KIU'
                elif 'AMADEUS' in source:
                    formato_final = 'PDF_AMA' if ext == '.pdf' else 'TXT_AMA'
            
            if formato_final:
                boleto.formato_detectado = formato_final
            elif source in [c[0] for c in boleto.FormatoDetectado.choices]:
                boleto.formato_detectado = source
            else:
                if ext == '.eml': boleto.formato_detectado = 'EML_GEN'
                else: boleto.formato_detectado = 'OTR'
            
            boleto.localizador_pnr = self._safe_truncate(
                d.get('pnr') or d.get('CODIGO_RESERVA') or d.get('localizador'), 20
            )

            boleto.numero_boleto = self._safe_truncate(
                d.get('ticket_number') or d.get('NUMERO_DE_BOLETO') or d.get('numero_boleto'), 50
            )
            
            logger.info(f"[ParserService] Buscando nombre en JSON para boleto {boleto.pk}. Llaves: {list(d.keys())[:15]}...")
            
            p_name = d.get('NOMBRE_DEL_PASAJERO') or d.get('passenger_name') or \
                     d.get('nombre_pasajero') or d.get('nombre_completo') or \
                     d.get('passenger name')
            
            if not p_name and isinstance(d.get('pasajero'), dict):
                p_name = d.get('pasajero').get('nombre_completo')
            
            if p_name: 
                logger.info(f"[ParserService] Nombre final a guardar: '{p_name}'")
                p_name = str(p_name).split(' FOID')[0].split(' RIF')[0].strip()

            boleto.nombre_pasajero_completo = self._safe_truncate(p_name, 150)
            
            p_proc = d.get('SOLO_NOMBRE_PASAJERO') or d.get('solo_nombre_pasajero') or p_name
            boleto.nombre_pasajero_procesado = self._safe_truncate(p_proc, 150)
            
            boleto.aerolinea_emisora = self._safe_truncate(d.get('NOMBRE_AEROLINEA') or d.get('issuing_airline'), 150)
            boleto.direccion_aerolinea = d.get('DIRECCION_AEROLINEA') or d.get('issuing_agent', {}).get('address')
            boleto.agente_emisor = self._safe_truncate(d.get('AGENTE_EMISOR') or d.get('issuing_agent', {}).get('name'), 150)
            boleto.foid_pasajero = self._safe_truncate(
                d.get('passenger_document') or d.get('CODIGO_IDENTIFICACION'), 50
            )
            
            tarifas = d.get('tarifas') or {}
            desglose = tarifas.get('taxes_breakdown') or d.get('taxes_breakdown') or {}
            
            def safe_decimal(val):
                if not val: return Decimal("0.00")
                try:
                    s = str(val).upper().replace('USD','').replace('EUR','').replace('BS','').replace('VES','').strip()
                    import re
                    match = re.search(r'[\d,.]+', s)
                    if not match: return Decimal("0.00")
                    num_str = match.group(0)
                    if ',' in num_str and '.' in num_str:
                        if num_str.find('.') < num_str.find(','):
                            num_str = num_str.replace('.', '').replace(',', '.')
                        else:
                            num_str = num_str.replace(',', '')
                    elif ',' in num_str:
                        num_str = num_str.replace(',', '.')
                    return Decimal(num_str)
                except:
                    return Decimal("0.00")
            
            total_str = tarifas.get('total_amount') or d.get('total_amount') or d.get('TOTAL') or d.get('total') or d.get('TOTAL_IMPORTE')
            boleto.total_boleto = safe_decimal(total_str)
            
            fare_str = tarifas.get('fare_amount') or d.get('fare_amount') or d.get('TARIFA_IMPORTE')
            boleto.tarifa_base = safe_decimal(fare_str)

            boleto.impuestos_descripcion = d.get('tax_details') or d.get('IMPUESTOS')
            if isinstance(boleto.impuestos_descripcion, dict):
                boleto.impuestos_descripcion = str(boleto.impuestos_descripcion)
            
            try: 
                boleto.iva_monto = safe_decimal(desglose.get('iva') or desglose.get('VAT'))
                boleto.inatur_monto = safe_decimal(desglose.get('inatur') or desglose.get('tourism_tax'))
                boleto.otros_impuestos_monto = safe_decimal(desglose.get('otros') or desglose.get('others') or desglose.get('other_taxes'))
                
                tax_total_raw = tarifas.get('taxes_amount') or d.get('taxes_amount') or d.get('IMPUESTOS')
                if tax_total_raw:
                    boleto.impuestos_total_calculado = safe_decimal(tax_total_raw)
                else:
                    boleto.impuestos_total_calculado = boleto.iva_monto + boleto.inatur_monto + boleto.otros_impuestos_monto
                
                logger.info(f"📊 [DEBUG] Impuestos Calculados: {boleto.impuestos_total_calculado}")
            except Exception as e:
                logger.error(f"❌ Error calculando impuestos: {e}")
                boleto.impuestos_total_calculado = Decimal("0.00")
            
            fecha_str = d.get('issue_date') or d.get('FECHA_DE_EMISION')
            if fecha_str:
                from core.ticket_parser import _parse_date_robust
                try:
                    fecha_obj = _parse_date_robust(fecha_str)
                    if fecha_obj:
                        boleto.fecha_emision_boleto = fecha_obj
                except Exception as e:
                    logger.warning(f"Error parseando fecha de emisión '{fecha_str}': {e}")
            
            if ('TOTAL_MONEDA' in d or 'moneda' in d) and 'total_currency' not in d:
                d['total_currency'] = d.get('moneda') or d.get('TOTAL_MONEDA')
            
            iata_code = d.get('agencia_iata') or d.get('agency_iata')
            if not iata_code and boleto.aerolinea_emisora:
                 from core.models_catalogos import Aerolinea
                 aero_obj = Aerolinea.objects.filter(nombre__icontains=boleto.aerolinea_emisora).first()
                 if aero_obj:
                     iata_code = aero_obj.codigo_iata

            office_id = d.get('office_id')
            proveedor_encontrado = self._buscar_proveedor_por_identificador(iata_code, office_id)
            if proveedor_encontrado:
                boleto.proveedor_emisor = proveedor_encontrado
            
            from core.airline_utils import validate_airline_numeric_code
            if boleto.numero_boleto and iata_code:
                es_valido = validate_airline_numeric_code(boleto.numero_boleto, iata_code)
                if not es_valido:
                    boleto.log_parseo = (boleto.log_parseo or "") + "\n⚠️ ADVERTENCIA: El número de boleto no coincide con el código IATA de la aerolínea."
            
            boleto.ruta_vuelo = d.get('ItinerarioFinalLimpio') or d.get('itinerary') or d.get('ruta')
            boleto.save()
            logger.info(f"Campos del modelo BoletoImportado {boleto.pk} actualizados.")

        except Exception as e:
            logger.error(f"Error actualizando campos del modelo boleto: {e}")

    def _gestionar_versionado(self, boleto):
        if not boleto.numero_boleto:
            return
        try:
            duplicados = BoletoImportado.objects.filter(
                numero_boleto=boleto.numero_boleto
            ).exclude(
                pk=boleto.pk
            ).order_by('-version', '-fecha_subida')

            ultimo_boleto = duplicados.first()

            if ultimo_boleto:
                logger.info(f"🔄 Versión detectada: Boleto {boleto.numero_boleto} ya existe (ID {ultimo_boleto.pk}, v{ultimo_boleto.version}).")
                boleto.version = ultimo_boleto.version + 1
                boleto.boleto_padre = ultimo_boleto
                boleto.estado_emision = BoletoImportado.EstadoEmision.REEMISION
                boleto.save()
        except Exception as e:
            logger.error(f"Error en gestión de versionado: {e}")

    def _buscar_proveedor_por_identificador(self, iata, office_id):
        if not iata and not office_id:
            return None
        try:
            from core.models_catalogos import Proveedor
            candidatos = Proveedor.objects.filter(Q(identificadores_gds__isnull=False))
            for prov in candidatos:
                gds_ids = prov.identificadores_gds
                if not isinstance(gds_ids, dict): continue
                
                if iata:
                    iatas = gds_ids.get('IATA', [])
                    if isinstance(iatas, list) and iata in iatas:
                        return prov
                
                if office_id:
                    offices = gds_ids.get('OFFICE_ID', [])
                    if isinstance(offices, list) and office_id in offices:
                        return prov
            return None
        except Exception as e:
            logger.error(f"Error buscando proveedor: {e}")
            return None

    @staticmethod
    def extraer_texto_desde_archivo(file_obj, filename):
        try:
            filename = filename.lower()
            if filename.endswith('.pdf'):
                texto_extraido = ""
                with pdfplumber.open(file_obj) as pdf:
                    for page in pdf.pages:
                        try:
                            text = page.extract_text()
                            if text: texto_extraido += text + "\n"
                        except Exception as e:
                            logger.warning(f"Error extrayendo página de PDF: {e}")
                            continue
                texto_pypdf = ""
                try:
                    reader = None
                    if pypdf: reader = pypdf.PdfReader(file_obj)
                    elif PyPDF2: reader = PyPDF2.PdfReader(file_obj)
                    
                    if reader:
                        file_obj.seek(0)
                        for page in reader.pages:
                            texto_pypdf += (page.extract_text() or "") + "\n"
                        if texto_pypdf:
                            texto_extraido += "\n\n--- FALLBACK EXTRACTION ---\n\n" + texto_pypdf
                except Exception as e_pypdf:
                    logger.warning(f"Fallback pypdf falló: {e_pypdf}")
                return texto_extraido
            
            elif filename.endswith('.eml'):
                msg = BytesParser(policy=policy.default).parse(file_obj)
                texto_final = "--- HEADERS START ---\n"
                essential_headers = ['Subject', 'From', 'To', 'Date']
                if hasattr(msg, 'items'):
                    for k, v in msg.items():
                        if k in essential_headers:
                            texto_final += f"{k}: {v}\n"
                texto_final += "--- HEADERS END ---\n\n"
                
                def clean_html_fragment(html_content):
                    if not BeautifulSoup: return html_content
                    try:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        for s in soup(["script", "style", "head", "title", "meta"]):
                            s.decompose()
                        text = soup.get_text(separator='\n')
                        return '\n'.join([l.strip() for l in text.splitlines() if l.strip()])
                    except:
                        return html_content

                html_found = False
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        try:
                            if ctype == 'text/html':
                                payload = part.get_payload(decode=True)
                                if not payload: continue
                                charset = part.get_content_charset() or 'utf-8'
                                content = payload.decode(charset, errors='replace')
                                texto_final += clean_html_fragment(content)
                                html_found = True
                            elif ctype == 'text/plain' and not html_found:
                                payload = part.get_payload(decode=True)
                                if not payload: continue
                                charset = part.get_content_charset() or 'utf-8'
                                content = payload.decode(charset, errors='replace')
                                texto_final += content
                        except: pass
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or 'utf-8'
                        content = payload.decode(charset, errors='replace')
                        if msg.get_content_type() == 'text/html':
                            texto_final += clean_html_fragment(content)
                        else:
                            texto_final += content
                return texto_final
            else:
                content = file_obj.read()
                return content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error extrayendo texto de archivo {filename}: {e}")
            return None

    def _extraer_texto(self, boleto):
        try:
            archivo_origen = self._obtener_archivo_abierto(boleto)
            nombre_archivo = boleto.archivo_boleto.name
            return self.extraer_texto_desde_archivo(archivo_origen, nombre_archivo)
        except Exception as e:
            logger.error(f"Error en _extraer_texto para boleto {boleto.pk}: {e}")
            return None

    def _obtener_archivo_abierto(self, boleto):
        if hasattr(boleto.archivo_boleto, 'url') and boleto.archivo_boleto.url.startswith('http'):
            try:
                response = requests.get(boleto.archivo_boleto.url, timeout=15)
                response.raise_for_status()
                return BytesIO(response.content)
            except Exception as e:
                logger.error(f"Error descargar boleto remoto: {e}")
                pass
        f = boleto.archivo_boleto.open('rb')
        f.seek(0)
        return f

    def _guardar_venta_acumulativa(self, boleto, datos, forced_client_id=None):
        """
        PUENTE HACIA VentaAutomationService:
        Mantiene compatibilidad pero delega al nuevo motor blindado.
        """
        from core.services.venta_automation import VentaAutomationService
        
        agencia = boleto.agencia # AgenciaMixin ya lo asegura
        
        # El user viene del thread local en el servicio automatizado
        return VentaAutomationService.crear_venta_desde_parser(
            parsed_data=datos,
            agencia=agencia,
            usuario=None # Se detecta por middleware si es posible
        )

    def _generar_y_guardar_pdf(self, boleto, datos):
        """
        Pivote final post-parsing: Renderiza el boleto HTML a un documento PDF via Weasyprint.
        Notifica a canales vía redes de broadcast.
        
        Args:
            boleto (BoletoImportado): Registro de DB vinculado.
            datos (dict): Data del pasajero y tarifas.
            
        # ⚡ ASÍNCRONO: Envío a Telegram Notification Channel para God Mode logs. (Acoplamiento débil).
        """
        try:
            from django.core.files.base import ContentFile
            logger.info(f"🎨 Generando PDF para boleto {boleto.pk} (Sistema: {datos.get('SOURCE_SYSTEM')})")
            
            pdf_bytes, filename = PdfGenerationService.generate_ticket(datos, agencia_obj=boleto.agencia)
            
            if pdf_bytes:
                boleto.archivo_pdf_generado.save(
                    f"Boleto_{boleto.pk}_{filename}",
                    ContentFile(pdf_bytes),
                    save=False
                )
                boleto.save(update_fields=['archivo_pdf_generado'])
                logger.info(f"✅ PDF Generado con éxito: {filename}")

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
                        if hasattr(boleto.archivo_pdf_generado, 'path'):
                            pdf_file_input = boleto.archivo_pdf_generado.path
                    except NotImplementedError:
                         if hasattr(boleto.archivo_pdf_generado, 'url'):
                             pdf_file_input = boleto.archivo_pdf_generado.url

                    if pdf_file_input:
                        storage_id = getattr(settings, 'TELEGRAM_STORAGE_CHANNEL_ID', None)
                        if boleto.agencia and boleto.agencia.configuracion_api.get('TELEGRAM_STORAGE_CHANNEL_ID'):
                            storage_id = boleto.agencia.configuracion_api.get('TELEGRAM_STORAGE_CHANNEL_ID')

                        file_id_generado = None
                        
                        if storage_id:
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

                        group_id = getattr(settings, 'TELEGRAM_GROUP_ID', None)
                        if group_id and group_id != storage_id:
                            logger.info(f"🔔 Enviando notificación a Grupo: {group_id}")
                            path_or_id = file_id_generado if file_id_generado and isinstance(file_id_generado, str) else pdf_file_input
                            
                            TelegramNotificationService.send_document(
                                file_path=path_or_id,
                                caption=caption,
                                chat_id=group_id,
                                agencia=boleto.agencia
                            )
                        
                        if boleto.telegram_file_id == 'SENDING' and not file_id_generado:
                            boleto.telegram_file_id = None
                            boleto.save(update_fields=['telegram_file_id'])
                    else:
                        logger.error(f"❌ No se pudo obtener Path ni URL del PDF para boleto {boleto.pk}")

                except Exception as e_tg:
                    logger.error(f"⚠️ Error enviando notificación Telegram en TicketParserService: {e_tg}")

            else:
                logger.warning(f"⚠️ generate_ticket retornó vacío para boleto {boleto.pk}")
                
        except Exception as e:
            logger.error(f"❌ Error generando PDF para boleto {boleto.pk}: {e}")
# =========================================================
# FUNCIONES ORQUESTADORAS (PUENTES)
# =========================================================

def orquestar_parseo_de_boleto(archivo_subido):
    """
    🏢 MULTI-TENANT | 🧠 IA
    Helper orquestador Standalone. Usado por la rest API (/api/boletos/upload/) o HTMX sin guardar modelo crudo base por adelantado.
    Parsea on-the-fly (útil si hay previews o pruebas de parser que no deben alterar tablas fiscales Venta).
    
    Args:
        archivo_subido (File/InMemoryUploadedFile): Payload directo HTTP.
        
    Returns:
        tuple[list|None, str]: Lista de dicts con la data parseada, o mensaje de Error si falla.
    """
    logger.info(f"🚀 Iniciando orquestación de parseo (API) para: {archivo_subido.name}")
    
    try:
        texto_extraido = TicketParserService.extraer_texto_desde_archivo(archivo_subido, archivo_subido.name)
        archivo_subido.seek(0)

        if not texto_extraido.strip():
            return None, "El archivo no contiene texto legible."

        from core.ticket_parser import extract_data_from_text
        
        path_pdf = None
        try:
            if hasattr(archivo_subido, 'temporary_file_path'):
                path_pdf = archivo_subido.temporary_file_path()
        except:
            pass

        parsed_data = extract_data_from_text(texto_extraido, pdf_path=path_pdf)
        
        if not parsed_data:
            return None, "Error: El motor de parseo no pudo extraer datos."

        if "error" in parsed_data:
             return None, parsed_data["error"]

        resultados_lista = []

        if isinstance(parsed_data, dict):
             if parsed_data.get('is_multi_pax') and 'tickets' in parsed_data:
                 resultados_lista = parsed_data['tickets']
             else:
                 resultados_lista = [parsed_data]
        elif hasattr(parsed_data, 'to_dict'):
            resultados_lista = [parsed_data.to_dict()]
        else:
            resultados_lista = []

        validos = []
        for datos in resultados_lista:
            if datos.get('pnr') != 'No encontrado' or \
               datos.get('ticket_number') != 'No encontrado' or \
               datos.get('NUMERO_DE_BOLETO') or \
               datos.get('NOMBRE_DEL_PASAJERO'):
                 validos.append(datos)
        
        if validos:
            return validos, "Parseo exitoso"
        else:
            return None, "No se pudieron extraer datos válidos del boleto"
        
    except Exception as e:
        logger.exception("Error en orquestar_parseo_de_boleto")
        return None, f"Excepción interna: {str(e)}"

def generar_pdf_en_memoria(datos, path_ignored=None, agencia_obj=None):
    try:
        pdf_bytes, filename = PdfGenerationService.generate_ticket(datos, agencia_obj=agencia_obj)
        return pdf_bytes
    except Exception as e:
        logger.error(f"Error en generar_pdf_en_memoria: {e}")
        return None
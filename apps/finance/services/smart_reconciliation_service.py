import json
import logging
from decimal import Decimal
from typing import Any

import pandas as pd
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.bookings.models import BoletoImportado
from apps.finance.models.reconciliacion import (
    ConciliacionBoleto,
    LineaReporteReconciliacion,
    ReporteReconciliacion,
)

logger = logging.getLogger(__name__)

# --- Pydantic Schemas para extracción de IA ---

class LineaCobro(BaseModel):
    ticket_number: str = Field(description="El número de boleto facturado, usualmente 10-13 dígitos. Ej: '1347258019382'. Extraerlo lo más limpio posible.")
    fare_cobrado: float = Field(description="Monto de la tarifa base (Fare/Net) que cobró el proveedor. 0.0 si es nulo.")
    taxes_cobrados: float = Field(description="Monto de los impuestos (Taxes) cobrados por el proveedor.")
    comision_cedida: float = Field(description="Comisión a favor de la agencia cedida por el proveedor en este boleto. Si es un cobro extra, será negativo.")
    total_cobrado: float = Field(description="Monto final liquidado y cobrado por el proveedor por este ticket (Suele ser Fare + Taxes - Comm).")
    raw_reference: str = Field(description="Breve texto original de la línea para auditoría visual rápida.")

class ReporteLiquidacionSchema(BaseModel):
    proveedor_detectado: str = Field(description="Nombre del proveedor o consolidador (Ej: SABRE, KIU, AMADEUS, TICKET_CONSOLIDATOR).")
    lineas_cobradas: list[LineaCobro] = Field(description="Array con todas las filas de boletos cobrados extraídas del reporte.")


class SmartReconciliationService:
    """
    Servicio encargado de digitalizar un reporte del proveedor usando IA (o Pandas si es puro)
    y luego cruzarlo contra la base de datos de TravelHub (`BoletoImportado`).
    """
    
    @classmethod
    def procesar_reporte(cls, reporte_id: str) -> None:
        """Flujo principal: Extraer -> Guardar Lineas -> Cruzar"""
        reporte = ReporteReconciliacion.objects.get(pk=reporte_id)
        reporte.estado = 'PROCESANDO'
        reporte.save(update_fields=['estado'])
        
        try:
            # 1. Digitalizar el Archivo
            datos_ia = cls._extraer_datos_archivo(reporte)
            
            # 2. Guardar las líneas crudas en la BD
            cls._guardar_lineas_extraidas(reporte, datos_ia)
            
            # 3. Módulo de Algoritmo de Cruce Matemático
            resumen = cls._ejecutar_cruce_conciliacion(reporte)
            
            # 4. Actualizar el estado final del reporte
            reporte.resumen_conciliacion = resumen
            if resumen.get('discrepancias', 0) > 0 or resumen.get('huerfanos_reporte', 0) > 0 or resumen.get('huerfanos_local', 0) > 0:
                reporte.estado = 'CON_DISCREPANCIAS'
            else:
                reporte.estado = 'CONCILIADO'
            reporte.save(update_fields=['resumen_conciliacion', 'estado'])
            
            logger.info(f"Reporte {reporte_id} procesado exitosamente con estado {reporte.estado}")
            
        except Exception as e:
            logger.exception(f"Error procesando el reporte {reporte_id}")
            reporte.estado = 'ERROR'
            reporte.error_log = str(e)
            reporte.save(update_fields=['estado', 'error_log'])
            raise
            
    @classmethod
    def _extraer_datos_archivo(cls, reporte: ReporteReconciliacion) -> dict[str, Any]:
        """Usa Pandas si es CSV/Excel, o el nuevo SupplierReportParser si es PDF/Texto ruidoso"""
        file_path = reporte.archivo.path
        
        # Inteligencia Artificial para PDFs y archivos complejos
        if file_path.lower().endswith(('.pdf', '.eml', '.txt')):
            logger.info(f"Usando SupplierReportParser para procesar {file_path}")
            
            text = ""
            if file_path.lower().endswith('.pdf'):
                import fitz
                try:
                    with fitz.open(file_path) as pdf:
                        for page in pdf:
                            t = page.get_text()
                            if t:
                                text += t + "\n"
                except Exception as e:
                    logger.error(f"Error extrayendo texto del PDF: {e}")
                    raise ValueError("No se pudo extraer texto del reporte PDF.") from e
            else:
                with open(file_path, encoding='utf-8', errors='ignore') as f:
                    text = f.read()

            from apps.automation.parsers.supplier_report_parser import SupplierReportParser
            parser = SupplierReportParser()
            resultado = parser.parse_report_text(text)
            
            reporte.proveedor = resultado.get('proveedor_nombre', 'Desconocido')
            reporte.save(update_fields=['proveedor'])
            return resultado

        # Pandas para archivos estructurados (CSV/Excel)
        elif file_path.lower().endswith(('.csv', '.xlsx', '.xls')):
            logger.info(f"Procesando archivo estructurado: {file_path}")
            try:
                if file_path.lower().endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                # Normalización de Columnas via IA (Mapeo Heurístico)
                return cls._mapear_columnas_df_con_ia(df, reporte.proveedor)
            except Exception as e:
                logger.error(f"Error procesando archivo estructurado con Pandas: {e}")
                raise ValueError(f"Error leyendo el archivo Excel/CSV: {str(e)}") from e
            
        raise ValueError(f"Tipo de archivo no soportado para: {file_path}")

    @classmethod
    def _mapear_columnas_df_con_ia(cls, df: pd.DataFrame, proveedor_hint: str) -> dict[str, Any]:
        """
        Si el Excel no tiene las columnas estándar, le pedimos a Gemini que las identifique
        basándose en una muestra de las primeras 5 filas.
        """
        from apps.automation.services.ai_engine import ai_engine
        
        # Tomar cabecera y muestra
        cabecera = list(df.columns)
        muestra = df.head(5).to_dict(orient='records')
        
        prompt = f"""
        Analiza las columnas de este reporte de ventas del proveedor {proveedor_hint}.
        Identifica a qué campo estándar de TravelHub corresponde cada columna del Excel.
        
        COLUMNAS ENCONTRADAS: {cabecera}
        MUESTRA DE DATOS: {json.dumps(muestra, default=str)}
        
        CAMPOS REQUERIDOS:
        - numero_boleto: El número de ticket (13 dígitos).
        - pnr: Localizador de reserva.
        - pasajero: Nombre del cliente.
        - tarifa_neta: Monto base.
        - impuestos: Suma de tasas/taxes.
        - comision_monto: Comisión a favor de la agencia.
        - total_pagar: Lo que se le debe al proveedor.
        
        Responde con un JSON que mapee el nombre de la columna original al campo estándar.
        Ejemplo: {{"COL_TICKET_ID": "numero_boleto", "BASE_FARE": "tarifa_neta", ...}}
        """
        
        try:
            mapping = ai_engine.call_gemini(prompt=prompt, temperature=0.0)
            
            # Renombrar columnas según el mapeo
            df = df.rename(columns=mapping)
            
            # Convertir a items
            items = []
            for _, row in df.iterrows():
                items.append({
                    "numero_boleto": str(row.get('numero_boleto', '')),
                    "pnr": str(row.get('pnr', '')),
                    "pasajero": str(row.get('pasajero', '')),
                    "tarifa_neta": float(row.get('tarifa_neta', 0)),
                    "impuestos": float(row.get('impuestos', 0)),
                    "comision_monto": float(row.get('comision_monto', 0)),
                    "total_pagar": float(row.get('total_pagar', 0)),
                    "moneda": "USD" # Default
                })
            
            return {
                "proveedor_nombre": proveedor_hint,
                "items": items
            }
        except Exception as e:
            logger.error(f"Fallo mapeando columnas con IA: {e}")
            # Fallback: intentar match directo si los nombres ya coinciden
            return {
                "proveedor_nombre": proveedor_hint,
                "items": df.to_dict(orient='records')
            }


    @classmethod
    @transaction.atomic
    def _guardar_lineas_extraidas(cls, reporte: ReporteReconciliacion, datos_ia: dict[str, Any]) -> None:
        """Toma el JSON nativo extraído por la IA y lo inserta en `LineaReporteReconciliacion`"""
        # Limpiar cruces previos si hubiere (por reprocesamiento)
        reporte.lineas.all().delete()
        
        # El nuevo schema usa 'items' en lugar de 'lineas_cobradas'
        lineas_schema = datos_ia.get('items', [])
        for item in lineas_schema:
            LineaReporteReconciliacion.objects.create(
                reporte=reporte,
                numero_boleto_reportado=item.get('numero_boleto', '').strip(),
                tarifa_base_cobrada=Decimal(str(item.get('tarifa_neta', 0))),
                impuestos_cobrados=Decimal(str(item.get('impuestos', 0))),
                comision_cedida=Decimal(str(item.get('comision_monto', 0))),
                total_cobrado=Decimal(str(item.get('total_pagar', 0))),
                raw_data=item
            )


    @classmethod
    @transaction.atomic
    def _ejecutar_cruce_conciliacion(cls, reporte: ReporteReconciliacion) -> dict[str, Any]:
        """Cruzador Financiero Híbrido: Batch + IA Fuzzy"""
        reporte.conciliaciones.all().delete()
        
        resumen = {
            'total_lineas': 0,
            'cuadrados_ok': 0,
            'discrepancias': 0,
            'huerfanos_reporte': 0,
            'huerfanos_local': 0
        }
        
        lineas_reporte = list(reporte.lineas.all())
        resumen['total_lineas'] = len(lineas_reporte)

        # 1. Obtener candidatos locales (Ventas de la agencia en un rango de fecha similar ±15 días)
        buffer_dias = 15
        query_local = BoletoImportado.objects.filter(agencia=reporte.agencia)
        if reporte.periodo_inicio:
            query_local = query_local.filter(fecha_emision__gte=reporte.periodo_inicio - timezone.timedelta(days=buffer_dias))
        if reporte.periodo_fin:
            query_local = query_local.filter(fecha_emision__lte=reporte.periodo_fin + timezone.timedelta(days=buffer_dias))

        ventas_locales = list(query_local.values('id_boleto', 'numero_boleto', 'pnr', 'pasajero_nombre_completo', 'total_boleto', 'tarifa_base', 'impuestos_total_calculado'))

        # 2. Match Determinístico Rápido (O(n) con diccionarios)
        boletos_asignados = set()
        lineas_procesadas = set()

        # Pre-construir índices para búsqueda O(1)
        ticket_index = {}
        pnr_index = {}
        for v in ventas_locales:
            num_loc = (v['numero_boleto'] or '').replace("-", "").strip()[-10:]
            if num_loc:
                ticket_index.setdefault(num_loc, []).append(v)
            pnr_val = (v['pnr'] or '').upper().strip()
            if pnr_val and len(pnr_val) == 6:
                pnr_index.setdefault(pnr_val, []).append(v)

        for linea in lineas_reporte:
            num_rep = linea.numero_boleto_reportado.replace("-", "").strip()[-10:]
            pnr_rep = (linea.raw_data or {}).get('pnr', '').upper().strip()

            match = None
            # Prioridad 1: Número de boleto (10 dígitos finales)
            if num_rep and num_rep in ticket_index:
                for v in ticket_index[num_rep]:
                    if v['id_boleto'] not in boletos_asignados:
                        match = v
                        break

            # Prioridad 2: PNR (Si no hubo match por boleto)
            if not match and pnr_rep and pnr_rep in pnr_index:
                for v in pnr_index[pnr_rep]:
                    if v['id_boleto'] not in boletos_asignados:
                        match = v
                        break

            if match:
                cls._crear_conciliacion(reporte, linea, match, resumen)
                boletos_asignados.add(match['id_boleto'])
                lineas_procesadas.add(linea.id_linea)

        # 3. Match Fuzzy con IA (Para lo que no tuvo match exacto)
        pendientes_reporte = lineas_reporte.exclude(id_linea__in=lineas_procesadas)
        pendientes_local = [v for v in ventas_locales if v['id_boleto'] not in boletos_asignados]
        
        if pendientes_reporte.exists() and pendientes_local:
            logger.info(f"🤖 Ejecutando Cruce Fuzzy IA para {pendientes_reporte.count()} líneas pendientes.")
            # Dividir en lotes de 20 para no saturar tokens/contexto
            from apps.common.utils.lists import chunk_list
            for chunk in chunk_list(list(pendientes_reporte), 20):
                cls._procesar_lote_fuzzy_ia(reporte, chunk, pendientes_local, boletos_asignados, resumen)

        # 4. Detectar Huérfanos finales (Reporte sin Local)
        huerfanos_reporte = lineas_reporte.exclude(id_linea__in=lineas_procesadas)
        for hr in huerfanos_reporte:
            if not hr.conciliacion: # Si no se creó en el paso fuzzy
                ConciliacionBoleto.objects.create(
                    reporte=reporte,
                    linea_reporte=hr,
                    estado=ConciliacionBoleto.EstadosCruce.NO_EN_LOCAL,
                    diferencia_total=hr.total_cobrado
                )
                resumen['huerfanos_reporte'] += 1

        # 5. Detectar Huérfanos locales (Local sin Reporte - Facturación pendiente)
        for vl in ventas_locales:
            if vl['id_boleto'] not in boletos_asignados:
                ConciliacionBoleto.objects.create(
                    reporte=reporte,
                    boleto_local_id=vl['id_boleto'],
                    estado=ConciliacionBoleto.EstadosCruce.NO_EN_REPORTE,
                    diferencia_total=-Decimal(str(vl['total_boleto'] or 0))
                )
                resumen['huerfanos_local'] += 1

        return resumen

    @classmethod
    def _crear_conciliacion(cls, reporte, linea, match_data, resumen):
        """Crea el registro de conciliación y calcula discrepancias"""
        total_local = Decimal(str(match_data['total_boleto'] or 0))
        dif_total = linea.total_cobrado - total_local
        
        estado = ConciliacionBoleto.EstadosCruce.OK
        if abs(dif_total) > Decimal('0.05'):
            estado = ConciliacionBoleto.EstadosCruce.DISCREPANCIA
            resumen['discrepancias'] += 1
        else:
            resumen['cuadrados_ok'] += 1
            
        conciliacion = ConciliacionBoleto.objects.create(
            reporte=reporte,
            linea_reporte=linea,
            boleto_local_id=match_data['id_boleto'],
            estado=estado,
            diferencia_tarifa=linea.tarifa_base_cobrada - Decimal(str(match_data['tarifa_base'] or 0)),
            diferencia_impuestos=linea.impuestos_cobrados - Decimal(str(match_data['impuestos_total_calculado'] or 0)),
            diferencia_total=dif_total
        )
        
        if estado == ConciliacionBoleto.EstadosCruce.DISCREPANCIA:
            cls.proponer_asiento_ajuste(conciliacion)

    @classmethod
    def _procesar_lote_fuzzy_ia(cls, reporte, chunk_lineas, pendientes_local, boletos_asignados, resumen):
        """Usa Gemini para encontrar matches semánticos en un lote de registros"""
        from apps.automation.services.ai_engine import ai_engine
        from apps.automation.services.prompts import RECONCILIATION_SYSTEM_PROMPT
        from core.models.ai_schemas import ConciliacionLoteSchema
        
        # Preparar data compacta
        prov_data = [{
            "id": item.id_linea,
            "tkt": item.numero_boleto_reportado,
            "psg": item.raw_data.get('pasajero', '') if item.raw_data else '',
            "amt": float(item.total_cobrado)
        } for item in chunk_lineas]
        
        local_data = [{
            "id": v['id_boleto'],
            "tkt": v['numero_boleto'],
            "psg": v['pasajero_nombre_completo'],
            "amt": float(v['total_boleto'] or 0)
        } for v in pendientes_local]
        
        prompt = f"LISTA_PROVEEDOR:\n{json.dumps(prov_data)}\n\nLISTA_AGENCIA:\n{json.dumps(local_data)}"
        
        try:
            resultado = ai_engine.call_gemini(
                prompt=prompt,
                response_schema=ConciliacionLoteSchema,
                system_instruction=RECONCILIATION_SYSTEM_PROMPT,
                temperature=0.0
            )
            
            for match in resultado.get('matches', []):
                linea_id = match.get('proveedor_item_id') # Enviamos id_linea como id
                venta_id = match.get('venta_id')
                
                if not linea_id or not venta_id:
                    continue
                
                linea_obj = next((item for item in chunk_lineas if item.id_linea == int(linea_id)), None)
                venta = next((v for v in pendientes_local if v['id_boleto'] == int(venta_id)), None)
                
                if linea_obj and venta and venta['id_boleto'] not in boletos_asignados:
                    cls._crear_conciliacion(reporte, linea_obj, venta, resumen)
                    boletos_asignados.add(venta['id_boleto'])
                    # Marcar razonamiento IA
                    c = ConciliacionBoleto.objects.filter(reporte=reporte, linea_reporte=linea_obj).last()
                    if c:
                        c.ia_razonamiento = match.get('comentario')
                        c.save(update_fields=['ia_razonamiento'])
                    
        except Exception as e:
            logger.error(f"Error en lote fuzzy IA: {e}")


    @classmethod
    def _get_cuenta_contable(cls, agencia, config_key: str, fallback_codigo: str, tipo_cuenta_fallback: str):
        """
        Busca una cuenta contable en la configuración de la agencia.
        Si no existe, usa el fallback_codigo.
        Si el fallback tampoco existe, busca la primera cuenta del tipo especificado.
        """
        from apps.contabilidad.models import PlanContable
        
        codigo = agencia.configuracion_contable.get(config_key, fallback_codigo)
        
        try:
            return PlanContable.objects.get(codigo_cuenta=codigo)
        except PlanContable.DoesNotExist:
            logger.warning(f"Cuenta {codigo} (key: {config_key}) no encontrada para agencia {agencia.nombre}. Usando fallback por tipo {tipo_cuenta_fallback}.")
            cuenta = PlanContable.objects.filter(tipo_cuenta=tipo_cuenta_fallback, permite_movimientos=True).first()
            if not cuenta:
                logger.error(f"¡CRÍTICO! No se encontró ninguna cuenta de tipo {tipo_cuenta_fallback} para la agencia {agencia.nombre}.")
            return cuenta

    @classmethod
    def proponer_asiento_ajuste(cls, conciliacion: ConciliacionBoleto) -> None:
        """
        Crea un asiento borrador compensando la diferencia.
        Lógica:
        - Si dif_total > 0 (Ej: BSP nos cobró $51 y vendimos en $50), la agencia pierde $1 (Gasto/Pérdida).
        - Si dif_total < 0 (Ej: BSP nos cobró $49 y vendimos en $50), la agencia gana $1 (Ingreso/Recuperación).
        """
        from apps.contabilidad.models import AsientoContable, DetalleAsiento
        from apps.finance.models.currencies import Moneda
        
        if conciliacion.estado != ConciliacionBoleto.EstadosCruce.DISCREPANCIA or conciliacion.diferencia_total == 0:
            return
            
        try:
            agencia = conciliacion.reporte.agencia
            # Placeholder de moneda. Asumimos USD para la lógica base.
            moneda_usd = Moneda.objects.filter(codigo_iso='USD').first()
            if not moneda_usd: 
                logger.warning("No se encontró la moneda USD para el asiento de ajuste.")
                return
            
            tipo = "Pérdida (Sobrecobro Proveedor)" if conciliacion.diferencia_total > 0 else "Ganancia (Ahorro Proveedor)"
            monto_abs = abs(conciliacion.diferencia_total)
            boleto = conciliacion.linea_reporte.numero_boleto_reportado if (conciliacion.linea_reporte and conciliacion.linea_reporte.numero_boleto_reportado) else str(conciliacion.id_conciliacion)
            
            # Obtener tasa BCV actual para BSD (VEN-NIF)
            from apps.contabilidad.services import ContabilidadService
            tasa_bcv = ContabilidadService.obtener_tasa_bcv(timezone.now().date())
            
            asiento = AsientoContable.objects.create(
                descripcion_general=f"Ajuste automático de Reconciliación. Boleto: {boleto}. {tipo}.",
                tipo_asiento=AsientoContable.TipoAsiento.AJUSTE,
                estado=AsientoContable.EstadoAsiento.BORRADOR,
                moneda=moneda_usd,
                referencia_documento=f"REC-{conciliacion.reporte.id_reporte.hex[:6]}",
                tasa_cambio_aplicada=tasa_bcv
            )
            
            # Obtener cuentas dinámicamente
            cuenta_proveedor = cls._get_cuenta_contable(
                agencia, 'CUENTA_PROVEEDOR_USD', '2.1.01.02', 'PA'
            )
                
            if conciliacion.diferencia_total > 0:
                # PÉRDIDA: Debit Gasto, Credit Proveedor (le debemos más al proveedor)
                cuenta_ajuste = cls._get_cuenta_contable(
                    agencia, 'CUENTA_GASTO_DEFAULT', '6.1.01', 'GA'
                )
                
                if not cuenta_ajuste or not cuenta_proveedor:
                    raise ValueError("Faltan cuentas contables críticas para generar el asiento de pérdida.")

                # Línea 1: DEUDORA (Gasto)
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=1,
                    cuenta_contable=cuenta_ajuste,
                    debe=monto_abs,
                    debe_bsd=monto_abs * tasa_bcv,
                    descripcion_linea=f"Gasto por discrepancia en boleto {boleto}"
                )
                # Línea 2: ACREEDORA (Proveedor)
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=2,
                    cuenta_contable=cuenta_proveedor,
                    haber=monto_abs,
                    haber_bsd=monto_abs * tasa_bcv,
                    descripcion_linea="Ajuste cuenta por pagar (Sobrecobro)"
                )
            else:
                # GANANCIA: Debit Proveedor (le debemos menos), Credit Ingreso
                cuenta_ajuste = cls._get_cuenta_contable(
                    agencia, 'CUENTA_INGRESO_DEFAULT', '4.1.01', 'IN'
                )

                if not cuenta_ajuste or not cuenta_proveedor:
                    raise ValueError("Faltan cuentas contables críticas para generar el asiento de ganancia.")
                
                # Línea 1: DEUDORA (Proveedor)
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=1,
                    cuenta_contable=cuenta_proveedor,
                    debe=monto_abs,
                    debe_bsd=monto_abs * tasa_bcv,
                    descripcion_linea="Ajuste cuenta por pagar (Ahorro)"
                )
                # Línea 2: ACREEDORA (Ingreso)
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=2,
                    cuenta_contable=cuenta_ajuste,
                    haber=monto_abs,
                    haber_bsd=monto_abs * tasa_bcv,
                    descripcion_linea=f"Ingreso por discrepancia a favor en boleto {boleto}"
                )

            asiento.calcular_totales()
            
            conciliacion.sugerencia_asiento = asiento
            conciliacion.save(update_fields=['sugerencia_asiento'])
            
            logger.info(f"Asiento borrador {asiento.id_asiento} (con detalles) propuesto para la Conciliación {conciliacion.id_conciliacion}")
            
        except Exception as e:
            logger.error(f"Fallo sugiriendo asiento para conciliación {conciliacion.id_conciliacion}: {str(e)}")

    @classmethod
    def _buscar_boleto_difuso_con_ia(cls, linea: LineaReporteReconciliacion) -> tuple[BoletoImportado | None, str | None]:
        """
        Usa la IA para buscar un boleto que no coincidió exactamente por número.
        Busca candidatos por monto similar y deja que Gemini decida el match semántico.
        """
        from apps.automation.services.ai_engine import ai_engine

        # 1. Buscar candidatos locales con montos similares (tolerancia 5%)
        # y que no estén ya conciliados.
        candidatos = BoletoImportado.objects.filter(
            total_boleto__gte=linea.total_cobrado * Decimal('0.95'),
            total_boleto__lte=linea.total_cobrado * Decimal('1.05'),
            conciliacionboleto__isnull=True
        ).order_by('-fecha_subida')[:10]
        
        if not candidatos.exists():
            return None, None
            
        # 2. Preparar el contexto para Gemini
        contexto_candidatos = []
        for c in candidatos:
            contexto_candidatos.append({
                "id": c.pk,
                "numero_boleto": c.numero_boleto,
                "pasajero": c.pasajero_nombre_completo,
                "total": float(c.total_boleto or 0),
                "fecha": str(c.fecha_emision)
            })
            
        prompt = f"""
        Identifica si alguno de estos boletos locales coincide con la línea del reporte del proveedor.
        El número de boleto puede tener errores tipográficos o estar truncado. Confía en el nombre y monto.
        
        LÍNEA DEL REPORTE:
        - Número Reportado: {linea.numero_boleto_reportado}
        - Total Cobrado: {linea.total_cobrado}
        - Datos Crudos: {linea.raw_data}
        
        CANDIDATOS LOCALES:
        {json.dumps(contexto_candidatos, indent=2)}
        
        Responde con un JSON:
        {{
            "match_encontrado": bool,
            "id_candidato": int_o_null,
            "razonamiento": "explicación breve"
        }}
        """
        
        class MatchResult(BaseModel):
            match_encontrado: bool
            id_candidato: int | None
            razonamiento: str

        try:
            res = ai_engine.call_gemini(
                prompt=prompt,
                response_schema=MatchResult,
                temperature=0.0
            )
            
            if res.get("match_encontrado") and res.get("id_candidato"):
                return BoletoImportado.objects.get(pk=res["id_candidato"]), res.get("razonamiento")
        except Exception as e:
            logger.error(f"Error en cruce difuso IA: {e}")
            
        return None, None

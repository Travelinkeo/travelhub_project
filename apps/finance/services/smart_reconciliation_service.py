import os
import io
import mimetypes
import pandas as pd
from typing import List, Dict, Optional, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.finance.models.reconciliacion import (
    ReporteReconciliacion,
    LineaReporteReconciliacion,
    ConciliacionBoleto
)
from apps.bookings.models import BoletoImportado
from core.gemini import analizar_documento_con_gemini_estructurado
from pydantic import BaseModel, Field

import logging
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
    lineas_cobradas: List[LineaCobro] = Field(description="Array con todas las filas de boletos cobrados extraídas del reporte.")


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
    def _extraer_datos_archivo(cls, reporte: ReporteReconciliacion) -> Dict[str, Any]:
        """Usa Pandas si es CSV/Excel, o el nuevo SupplierReportParser si es PDF/Texto ruidoso"""
        file_path = reporte.archivo.path
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Inteligencia Artificial para PDFs y archivos complejos
        if mime_type == 'application/pdf' or file_path.lower().endswith('.pdf') or file_path.lower().endswith('.eml'):
            logger.info(f"Usando SupplierReportParser para procesar {file_path}")
            
            # Extraer texto del PDF (o EML si fuera necesario)
            import pdfplumber
            text = ""
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
            except Exception as e:
                logger.error(f"Error extrayendo texto del PDF: {e}")
                raise ValueError("No se pudo extraer texto del reporte PDF.")

            from core.parsers.supplier_report_parser import SupplierReportParser
            parser = SupplierReportParser()
            resultado = parser.parse_report_text(text)
            
            reporte.proveedor = resultado.get('proveedor_nombre', 'Desconocido')
            reporte.save(update_fields=['proveedor'])
            return resultado

        # Pandas para archivos CSV estructurados (Ahorrar llamadas a la IA si es posible)
        elif file_path.lower().endswith('.csv'):
            logger.info("Procesando CSV con Pandas.")
            df = pd.read_csv(file_path)
            # Todo: Mapeo heurístico de columnas si son CSV crudos (Se completará según necesidades del usuario)
            # Por ahora lo mandamos también a la IA simulando texto si no conocemos las columnas.
            
        raise ValueError(f"Tipo de archivo no soportado o flujo no implemetado para: {mime_type}")

    @classmethod
    @transaction.atomic
    def _guardar_lineas_extraidas(cls, reporte: ReporteReconciliacion, datos_ia: Dict[str, Any]) -> None:
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
    def _ejecutar_cruce_conciliacion(cls, reporte: ReporteReconciliacion) -> Dict[str, int]:
        """Cruzador Financiero: Reporte Proveedor VS Base de Datos de TravelHub"""
        # Primero borrar las conciliaciones pre-existentes de este reporte
        reporte.conciliaciones.all().delete()
        
        resumen = {
            'total_lineas': 0,
            'cuadrados_ok': 0,
            'discrepancias': 0,
            'huerfanos_reporte': 0, # Cobrados pero no los tenemos
            'huerfanos_local': 0    # Los tenemos pero no los cobraron
        }
        
        lineas = reporte.lineas.all()
        resumen['total_lineas'] = lineas.count()
        
        numeros_procesados = []
        boletos_asignados_en_cruce = set()

        # 1. Cruce del Reporte hacia Local (Match Robusto)
        for linea in lineas:
            num_reportado = linea.numero_boleto_reportado.replace("-", "").strip()
            # Standard IATA: Los últimos 10 dígitos suelen ser el ID único sin código de aerolínea
            busqueda_sufijo = num_reportado[-10:] if len(num_reportado) >= 10 else num_reportado
            
            # Buscamos candidatos que NO estén ya vinculados a este reporte
            boleto = BoletoImportado.objects.filter(
                agencia=reporte.agencia,
                numero_boleto__icontains=busqueda_sufijo
            ).exclude(id_boleto__in=boletos_asignados_en_cruce).first()

            ia_razonamiento = None
            if not boleto:
                # --- FUZZY MATCHING CON IA ASINCRÓNICO/SIMULADO ---
                logger.info(f"Boleto {num_reportado} no encontrado exactamente. Intentando Cruce Difuso IA...")
                boleto, ia_razonamiento = cls._buscar_boleto_difuso_con_ia(linea)

            if not boleto:
                ConciliacionBoleto.objects.create(
                    reporte=reporte,
                    linea_reporte=linea,
                    boleto_local=None,
                    estado=ConciliacionBoleto.EstadosCruce.NO_EN_LOCAL,
                    diferencia_total=linea.total_cobrado
                )
                resumen['huerfanos_reporte'] += 1
                continue

            boletos_asignados_en_cruce.add(boleto.id_boleto)
            numeros_procesados.append(boleto.numero_boleto)
            
            # 2. Comparación de Costos (Basado en el Plan de Cuentas)
            total_local = Decimal(str(boleto.total_boleto or 0))
            dif_total = linea.total_cobrado - total_local
            
            estado = ConciliacionBoleto.EstadosCruce.OK
            if abs(dif_total) > Decimal('0.05'): # Tolerancia de 5 centavos para redondeos
                estado = ConciliacionBoleto.EstadosCruce.DISCREPANCIA
                resumen['discrepancias'] += 1
            else:
                resumen['cuadrados_ok'] += 1

            ConciliacionBoleto.objects.create(
                reporte=reporte,
                linea_reporte=linea,
                boleto_local=boleto,
                estado=estado,
                diferencia_tarifa=linea.tarifa_base_cobrada - (boleto.tarifa_base or 0),
                diferencia_impuestos=linea.impuestos_cobrados - (boleto.impuestos_total_calculado or 0),
                diferencia_total=dif_total,
                ia_razonamiento=ia_razonamiento
            )

            # Sugerir asiento contable de compensación si hay discrepancia
            if estado == ConciliacionBoleto.EstadosCruce.DISCREPANCIA:
                cls.proponer_asiento_ajuste(reporte.conciliaciones.last())
            
        # 2. Cruce Local hacia el Reporte (Detectar Facturación Pendiente)
        # Opcional: Buscar Boletos en ese período que NO vinieron en este reporte
        if reporte.periodo_inicio and reporte.periodo_fin:
             boletos_periodo = BoletoImportado.objects.filter(
                 fecha_subida__gte=reporte.periodo_inicio,
                 fecha_subida__lte=reporte.periodo_fin
             ).exclude(numero_boleto__in=numeros_procesados)
             
             for huerfano in boletos_periodo:
                 ConciliacionBoleto.objects.create(
                    reporte=reporte,
                    linea_reporte=None,
                    boleto_local=huerfano,
                    estado=ConciliacionBoleto.EstadosCruce.NO_EN_REPORTE,
                    diferencia_total=-(huerfano.total_boleto or Decimal(0))
                 )
                 resumen['huerfanos_local'] += 1
                 
        return resumen

    @classmethod
    def proponer_asiento_ajuste(cls, conciliacion: ConciliacionBoleto) -> None:
        """
        Crea un asiento borrador compensando la diferencia.
        Lógica:
        - Si dif_total > 0 (Ej: BSP nos cobró $51 y vendimos en $50), la agencia pierde $1 (Gasto/Pérdida).
        - Si dif_total < 0 (Ej: BSP nos cobró $49 y vendimos en $50), la agencia gana $1 (Ingreso/Recuperación).
        """
        from apps.contabilidad.models import AsientoContable, PlanContable, DetalleAsiento
        from core.models_catalogos import Moneda
        
        if conciliacion.estado != ConciliacionBoleto.EstadosCruce.DISCREPANCIA or conciliacion.diferencia_total == 0:
            return
            
        try:
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
            
            # Definir cuentas (fallbacks si no existen las específicas)
            # 2.1.01.02 -> Cuentas por Pagar Proveedores USD
            # 6.1.01 -> Gastos de Operación (Genérico)
            # 4.1.01 -> Ingresos por Comisiones (Genérico)
            
            try:
                cuenta_proveedor = PlanContable.objects.get(codigo_cuenta='2.1.01.02')
            except PlanContable.DoesNotExist:
                cuenta_proveedor = PlanContable.objects.filter(tipo_cuenta='PA', permite_movimientos=True).first()
                
            if conciliacion.diferencia_total > 0:
                # PÉRDIDA: Debit Gasto, Credit Proveedor (le debemos más al proveedor)
                try:
                    cuenta_ajuste = PlanContable.objects.get(codigo_cuenta='6.1.01') # Gastos Operativos
                except PlanContable.DoesNotExist:
                    cuenta_ajuste = PlanContable.objects.filter(tipo_cuenta='GA', permite_movimientos=True).first()
                
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
                    descripcion_linea=f"Ajuste cuenta por pagar (Sobrecobro)"
                )
            else:
                # GANANCIA: Debit Proveedor (le debemos menos), Credit Ingreso
                try:
                    cuenta_ajuste = PlanContable.objects.get(codigo_cuenta='4.1.01') # Ingresos Operativos
                except PlanContable.DoesNotExist:
                    cuenta_ajuste = PlanContable.objects.filter(tipo_cuenta='IN', permite_movimientos=True).first()
                
                # Línea 1: DEUDORA (Proveedor)
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=1,
                    cuenta_contable=cuenta_proveedor,
                    debe=monto_abs,
                    debe_bsd=monto_abs * tasa_bcv,
                    descripcion_linea=f"Ajuste cuenta por pagar (Ahorro)"
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
    def _buscar_boleto_difuso_con_ia(cls, linea: LineaReporteReconciliacion) -> tuple[Optional[BoletoImportado], Optional[str]]:
        """
        Usa la IA para buscar un boleto que no coincidió exactamente por número.
        Busca candidatos por monto similar y deja que Gemini decida el match semántico.
        """
        from core.services.ai_engine import ai_engine
        import json

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
            id_candidato: Optional[int]
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

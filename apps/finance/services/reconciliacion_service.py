import logging
import fitz  # PyMuPDF
from decimal import Decimal, InvalidOperation
from django.db import transaction
from core.models import BoletoImportado
from core.report_parser import parse_travelinkeo_report_with_gemini
from apps.finance.models import ReporteReconciliacion, DiferenciaFinanciera

logger = logging.getLogger(__name__)

class ReconciliacionService:
    """
    Servicio SaaS para procesar reportes financieros y conciliarlos con las ventas.
    """
    
    def __init__(self, reporte: ReporteReconciliacion):
        self.reporte = reporte
        self.agencia = reporte.agencia

    def procesar_reporte(self):
        """
        Orquesta el flujo completo de conciliación: Extracción -> Parsing AI -> Matching -> Resultados.
        """
        try:
            self.reporte.estado = 'PROCESANDO'
            self.reporte.save(update_fields=['estado'])
            
            # 1. Extraer texto del archivo
            texto_pdf = self._extraer_texto_pdf()
            if not texto_pdf:
                raise ValueError("No se pudo extraer texto del archivo PDF.")
            
            # 2. Parsear con IA (Gemini)
            datos_parsed = parse_travelinkeo_report_with_gemini(texto_pdf)
            if not datos_parsed:
                raise ValueError("La IA no pudo estructurar los datos del reporte.")
            
            self.reporte.datos_extraidos = datos_parsed
            self.reporte.save(update_fields=['datos_extraidos'])
            
            # 3. Conciliar
            resultados = self._conciliar_datos(datos_parsed)
            
            # 4. Guardar resultados finales
            self.reporte.resumen_conciliacion = resultados
            self.reporte.estado = 'CON_DISCREPANCIAS' if resultados['discrepancias'] > 0 else 'CONCILIADO'
            self.reporte.save(update_fields=['resumen_conciliacion', 'estado'])
            
            return True, f"Procesado: {resultados['total_registros']} registros. Discrepancias: {resultados['discrepancias']}"

        except Exception as e:
            logger.exception(f"Error procesando reporte {self.reporte.id_reporte}: {e}")
            self.reporte.estado = 'ERROR'
            self.reporte.error_log = str(e)
            self.reporte.save(update_fields=['estado', 'error_log'])
            return False, str(e)

    def _extraer_texto_pdf(self):
        """Usa PyMuPDF para extraer texto raw."""
        try:
            texto = ""
            with self.reporte.archivo.open('rb') as f:
                contenido = f.read()
                import io
                with fitz.open(stream=contenido, filetype="pdf") as doc:
                    for page in doc:
                        texto += page.get_text()
            return texto
        except Exception as e:
            logger.error(f"Error leyendo PDF: {e}")
            return None

    def _conciliar_datos(self, datos_parsed):
        """Comparar datos del reporte con la BD de la agencia."""
        stats = {
            'total_registros': len(datos_parsed),
            'encontrados': 0,
            'no_encontrados': 0,
            'discrepancias': 0,
            'ok': 0
        }
        
        for item in datos_parsed:
            ticket_number = item.get('numero_boleto')
            monto_reporte_str = item.get('monto_a_pagar')
            
            if not ticket_number:
                continue
                
            try:
                # Buscar boleto SOLO de esta agencia
                boleto = BoletoImportado.objects.filter(
                    numero_boleto__endswith=ticket_number[-10:], # Match flexible últimos 10 dígitos
                    agencia=self.agencia
                ).first()
                
                if boleto:
                    stats['encontrados'] += 1
                    monto_db = boleto.total_a_pagar or Decimal('0.0')
                    monto_reporte = Decimal(str(monto_reporte_str))
                    
                    if abs(monto_db - monto_reporte) > Decimal('0.5'): # Tolerancia 0.50
                        stats['discrepancias'] += 1
                        # Crear registro de discrepancia (Futuro)
                        # self._registrar_discrepancia(boleto, monto_db, monto_reporte)
                    else:
                        stats['ok'] += 1
                else:
                    stats['no_encontrados'] += 1
                    
            except Exception as e:
                logger.warning(f"Error cotejando boleto {ticket_number}: {e}")
                
        return stats

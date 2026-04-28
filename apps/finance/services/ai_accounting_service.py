import logging
import json
from datetime import datetime, timedelta
# import google.generativeai as genai
from django.conf import settings
from django.db.models import Sum, Count
from django.utils import timezone

from apps.bookings.models import Venta
from apps.crm.models import Cliente
from apps.finance.models import Factura, ItemReporte, DiferenciaFinanciera
from core.models.contabilidad import PlanContable, AsientoContable
from core.models_catalogos import Moneda

logger = logging.getLogger(__name__)

class AIAccountingService:
    """
    Servicio de Asistente Financiero y Contable con IA (Gemini Pro).
    Unifica análisis de ventas, conciliación y sugerencia de asientos.
    """
    
    def __init__(self, agencia):
        self.agencia = agencia
        from google import genai
        from google.genai import types as genai_types
        self._genai_types = genai_types
        self.api_key = settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-2.0-flash'
        self._system_instruction = f"""
            Eres el 'CFO Virtual' experto de la agencia '{agencia.nombre}'. 
            Tu misión es proporcionar análisis financiero preciso y asistencia contable.
            
            Reglas críticas:
            1. Habla en Español de forma profesional pero accesible.
            2. Formatea montos monetarios (ej: $1,250.00).
            3. Considera las normativas de Venezuela (IVA 16%, IGTF 3%) si la consulta lo requiere.
            """
        # Herramientas de Inteligencia Financiera
        self.tools = [
            self.get_financial_kpis,
            self.get_ventas_periodo,
            self.get_deuda_clientes,
            self.analyze_reconciliation_discrepancy,
            self.propose_accounting_entry,
            self.get_account_balance
        ]

    def ask(self, user_message):
        try:
            # Recopilar contexto de herramientas automáticamente
            kpis = self.get_financial_kpis()
            contexto = f"KPIs actuales: {kpis}\n\nPregunta del usuario: {user_message}"
            
            full_prompt = f"{self._system_instruction}\n\n{contexto}"
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Error en AI Accounting Service: {e}")
            return "Lo siento, tuve un problema analizando los datos financieros de la agencia."


    # --- TOOLS ---

    def get_financial_kpis(self):
        """Obtiene indicadores clave: Total ventas confirmadas, gastos del mes y rentabilidad bruta."""
        primer_dia_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        ventas = Venta.objects.filter(agencia=self.agencia, fecha_venta__gte=primer_dia_mes)
        total_ventas = ventas.aggregate(s=Sum('total_venta'))['s'] or 0
        
        from apps.finance.models import GastoOperativo
        gastos = GastoOperativo.objects.filter(agencia=self.agencia, fecha__gte=primer_dia_mes.date())
        total_gastos = gastos.aggregate(s=Sum('monto'))['s'] or 0
        
        return {
            "mes_actual": primer_dia_mes.strftime("%B %Y"),
            "total_ventas": float(total_ventas),
            "total_gastos_operativos": float(total_gastos),
            "utilidad_bruta_estimada": float(total_ventas - total_gastos),
            "moneda": "USD"
        }

    def get_ventas_periodo(self, dias: int = 30):
        """Consulta el volumen de ventas y cantidad de operaciones en los últimos N días."""
        fecha_inicio = timezone.now() - timedelta(days=dias)
        ventas = Venta.objects.filter(agencia=self.agencia, fecha_venta__gte=fecha_inicio)
        total = ventas.aggregate(total=Sum('total_venta'))['total'] or 0
        
        return {
            "periodo_dias": dias,
            "monto_total": float(total),
            "conteo": ventas.count()
        }

    def get_deuda_clientes(self):
        """Lista los 10 clientes con mayor deuda pendiente (facturas emitidas no pagadas)."""
        pendientes = Factura.objects.filter(
            agencia=self.agencia, 
            saldo_pendiente__gt=0, 
            estado__in=['EMI', 'PAR', 'VEN']
        ).values('cliente_nombre').annotate(
            deuda=Sum('saldo_pendiente'),
            facturas=Count('id_factura')
        ).order_by('-deuda')[:10]
        
        return [dict(cliente=p['cliente_nombre'], monto=float(p['deuda']), items=p['facturas']) for p in pendientes]

    def get_account_balance(self, codigo_cuenta: str):
        """Consulta detalles y saldo (simulado) de una cuenta del Plan Contable."""
        try:
            cuenta = PlanContable.objects.get(codigo_cuenta=codigo_cuenta)
            return {
                "nombre": cuenta.nombre_cuenta,
                "codigo": cuenta.codigo_cuenta,
                "naturaleza": cuenta.get_naturaleza_display(),
                "permite_movimientos": cuenta.permite_movimientos
            }
        except PlanContable.DoesNotExist:
            return {"error": f"La cuenta {codigo_cuenta} no existe."}

    def analyze_reconciliation_discrepancy(self, numero_boleto: str):
        """Analiza discrepancia entre reporte de proveedor y sistema para un boleto."""
        item = ItemReporte.objects.filter(reporte__agencia=self.agencia, numero_boleto=numero_boleto).first()
        if not item: return {"error": "Boleto no encontrado en conciliaciones."}
        
        diffs = item.diferencias.all()
        return {
            "boleto": item.numero_boleto,
            "estado": item.get_estado_display(),
            "monto_sistema": float(item.monto_sistema),
            "monto_proveedor": float(item.monto_total_proveedor),
            "diferencias": [{"campo": d.campo_discrepancia, "dif": float(d.diferencia)} for d in diffs]
        }

    def propose_accounting_entry(self, documento_tipo: str, documento_id: int):
        """Genera una propuesta de asiento para una Factura o Gasto."""
        # Lógica simplificada para el asistente
        return {
            "propuesta": "Asiento sugerido generado",
            "glosa": f"Registro de {documento_tipo} ID {documento_id}",
            "detalles": [
                {"cuenta": "1.1.01.01", "desc": "Caja/Bancos", "debe": 100.0, "haber": 0},
                {"cuenta": "4.1.01.01", "desc": "Ingresos por Servicios", "debe": 0, "haber": 100.0}
            ]
        }

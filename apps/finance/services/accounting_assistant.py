import os
import json
import logging
import google.generativeai as genai
from django.conf import settings
from django.db import models
from apps.finance.models import ItemReporte, DiferenciaFinanciera, ReporteProveedor
from core.models.contabilidad import PlanContable, AsientoContable, DetalleAsiento
from decimal import Decimal

logger = logging.getLogger(__name__)

class AccountingAssistantService:
    """
    Servicio que utiliza Gemini 2.0 Flash con Function Calling para actuar como
    un experto contable dentro de TravelHub.
    """

    def __init__(self, agencia):
        self.agencia = agencia
        self.api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
        if self.api_key:
            genai.configure(api_key=self.api_key, transport="rest")
            self.model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                tools=[
                    self.get_account_balance,
                    self.analyze_reconciliation_discrepancy,
                    self.list_pending_discrepancies,
                    self.propose_adjustment_entry
                ]
            )
            self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    def ask(self, question: str) -> str:
        """Procesa una pregunta del usuario y retorna la respuesta de la IA."""
        if not self.api_key:
            return "Error: API Key de Gemini no configurada."
        
        try:
            full_prompt = f"[Contexto: Agencia {self.agencia.nombre}] {question}"
            response = self.chat.send_message(full_prompt)
            return response.text
        except Exception as e:
            logger.exception("Error en AccountingAssistantService.ask")
            return f"Lo siento, hubo un error técnico al procesar tu consulta contable: {str(e)}"

    # --- Herramientas de Inteligencia Contable (Tools) ---

    def get_account_balance(self, codigo_cuenta: str) -> str:
        """
        Consulta el saldo y naturaleza de una cuenta contable específica.
        Args:
            codigo_cuenta: El código de la cuenta (ej: '1.1.01.01').
        """
        try:
            cuenta = PlanContable.objects.get(codigo_cuenta=codigo_cuenta)
            # Nota: En una fase real, aquí calcularíamos el saldo sumando DetalleAsiento.
            # Por ahora, devolvemos la naturaleza y descripción.
            return json.dumps({
                "cuenta": cuenta.nombre_cuenta,
                "codigo": cuenta.codigo_cuenta,
                "naturaleza": cuenta.get_naturaleza_display(),
                "tipo": cuenta.get_tipo_cuenta_display(),
                "saldo_estimado": "Requiere mayorista de asientos (Simulacion: $1,250.00)"
            })
        except PlanContable.DoesNotExist:
            return f"Error: La cuenta {codigo_cuenta} no existe en el Plan de Cuentas."

    def analyze_reconciliation_discrepancy(self, numero_boleto: str) -> str:
        """
        Analiza detalladamente por qué un boleto tiene una discrepancia financiera.
        Args:
            numero_boleto: El número del ticket a analizar.
        """
        try:
            item = ItemReporte.objects.filter(
                reporte__agencia=self.agencia,
                numero_boleto=numero_boleto
            ).select_related('boleto_interno').first()

            if not item:
                return f"No encontré registros de conciliación para el boleto {numero_boleto}."

            diferencias = item.diferencias.all()
            diff_list = []
            for d in diferencias:
                diff_list.append({
                    "campo": d.campo_discrepancia,
                    "sistema": float(d.valor_sistema),
                    "proveedor": float(d.valor_proveedor),
                    "diferencia": float(d.diferencia)
                })

            context = {
                "boleto": item.numero_boleto,
                "pasajero": item.pasajero,
                "pnr": item.pnr,
                "estado": item.get_estado_display(),
                "diferencias_detectadas": diff_list,
                "total_sistema": float(item.monto_sistema),
                "total_proveedor": float(item.monto_total_proveedor)
            }
            
            return json.dumps(context)
        except Exception as e:
            return f"Error analizando discrepancia: {str(e)}"

    def list_pending_discrepancies(self) -> str:
        """Enumera las discrepancias financieras pendientes de resolución para la agencia."""
        try:
            items = ItemReporte.objects.filter(
                reporte__agencia=self.agencia,
                estado='DIS' # Discrepancy
            )[:10]
            
            resumen = []
            for i in items:
                resumen.append({
                    "ticket": i.numero_boleto,
                    "pasajero": i.pasajero,
                    "monto_diff": float(i.monto_total_proveedor - i.monto_sistema)
                })
            
            return json.dumps(resumen)
        except Exception:
            return "Error listando discrepancias."

    def propose_adjustment_entry(self, numero_boleto: str) -> str:
        """
        Genera una propuesta de asiento contable para corregir una discrepancia.
        Args:
            numero_boleto: El número del ticket que necesita el ajuste.
        """
        try:
            item = ItemReporte.objects.filter(
                reporte__agencia=self.agencia,
                numero_boleto=numero_boleto,
                estado='DIS'
            ).first()

            if not item:
                return "No hay discrepancia pendiente para este boleto que requiera ajuste."

            diff_total = float(item.monto_total_proveedor - item.monto_sistema)
            
            # Lógica simple: Si falta dinero en sistema, cargamos a Gastos y abonamos a Cuentas por Pagar Agencia
            propuesta = {
                "glosa": f"Ajuste por diferencia de conciliacion - Tkt {numero_boleto}",
                "fecha": str(timezone.now().date()),
                "items": [
                    {"cuenta": "6.1.01 (Gastos Operativos)", "debe": abs(diff_total) if diff_total > 0 else 0, "haber": 0 if diff_total > 0 else abs(diff_total)},
                    {"cuenta": "2.1.01 (Cuentas por Pagar)", "debe": 0 if diff_total > 0 else abs(diff_total), "haber": abs(diff_total) if diff_total > 0 else 0}
                ],
                "explicacion": f"Se propone un ajuste de {abs(diff_total)} para igualar el saldo del sistema con el reporte del proveedor."
            }
            
            return json.dumps(propuesta)
        except Exception as e:
            return f"Error generando propuesta: {str(e)}"

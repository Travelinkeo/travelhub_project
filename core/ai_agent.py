import os
import json
import google.generativeai as genai
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Venta, Factura, Cliente, Proveedor
from cotizaciones.models import Cotizacion
from apps.crm.models import Cliente as PersonaCliente

class TravelHubAgent:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        self.context = self._build_business_context()
    
    def _build_business_context(self):
        """Construye el contexto de negocio para el agente"""
        return """
        Eres el Agente Inteligente de TravelHub, el asistente IA de Travelinkeo, una agencia de viajes venezolana.
        
        INFORMACIÓN DE LA EMPRESA:
        - Nombre: Travelinkeo
        - Tipo: Agencia de viajes especializada
        - Servicios: Boletos aéreos, hoteles, paquetes turísticos, seguros de viaje
        - Mercado: Venezuela y internacional
        
        CAPACIDADES DEL SISTEMA:
        - Gestión de ventas y cotizaciones
        - Facturación automática
        - Seguimiento de pagos
        - Gestión de clientes y proveedores
        - Parseo automático de boletos (KIU, SABRE, AMADEUS)
        
        PERSONALIDAD:
        - Profesional pero amigable
        - Experto en turismo y viajes
        - Proactivo en sugerir mejoras
        - Habla en español venezolano
        - Usa emojis ocasionalmente para ser más cercano
        
        INSTRUCCIONES:
        - Siempre responde en español
        - Proporciona datos específicos cuando sea posible
        - Sugiere acciones concretas
        - Si no tienes información suficiente, pregunta por más detalles
        - Mantén respuestas concisas pero informativas
        """
    
    async def process_query(self, user_message, user_context=None):
        """Procesa una consulta del usuario"""
        try:
            # Obtener datos del sistema
            system_data = self._get_system_data()
            
            # Respuestas inteligentes basadas en palabras clave
            message_lower = user_message.lower()
            
            if any(word in message_lower for word in ['ventas', 'venta', 'vendido']):
                return self._handle_sales_query(system_data)
            elif any(word in message_lower for word in ['pago', 'pagos', 'cobrar', 'pendiente']):
                return self._handle_payments_query(system_data)
            elif any(word in message_lower for word in ['cotizacion', 'cotizaciones', 'presupuesto']):
                return self._handle_quotes_query(system_data)
            elif any(word in message_lower for word in ['cliente', 'clientes']):
                return self._handle_clients_query(system_data)
            elif any(word in message_lower for word in ['resumen', 'dashboard', 'estadisticas']):
                return self._handle_summary_query(system_data)
            else:
                return self._handle_general_query(system_data)
                
        except Exception as e:
            return f"Lo siento, ocurrió un error al procesar tu consulta: {str(e)}"
    
    def _handle_sales_query(self, data):
        ventas_mes = data.get('ventas_este_mes', {'total': 0, 'cantidad': 0})
        ventas_30d = data.get('ventas_ultimos_30d', {'total': 0, 'cantidad': 0})
        
        return f"""📊 **Resumen de Ventas**

**Este mes:**
• Total: ${ventas_mes['total']:,.2f}
• Cantidad: {ventas_mes['cantidad']} ventas

**Últimos 30 días:**
• Total: ${ventas_30d['total']:,.2f}
• Cantidad: {ventas_30d['cantidad']} ventas

¿Te gustaría ver más detalles sobre algún período específico?"""
    
    def _handle_payments_query(self, data):
        pendientes = data.get('pendientes_pago', {'total': 0, 'cantidad': 0})
        
        return f"""💰 **Estado de Pagos**

**Pendientes de cobro:**
• Monto total: ${pendientes['total']:,.2f}
• Número de ventas: {pendientes['cantidad']}

{'🔴 Tienes pagos pendientes que requieren seguimiento.' if pendientes['cantidad'] > 0 else '✅ ¡Excelente! No tienes pagos pendientes.'}

¿Quieres que te ayude a generar recordatorios de pago?"""
    
    def _handle_quotes_query(self, data):
        cotizaciones = data.get('cotizaciones_recientes', [])
        
        if not cotizaciones:
            return "📋 **Cotizaciones**\n\nNo tienes cotizaciones recientes en los últimos 30 días.\n\n¿Te gustaría crear una nueva cotización?"
        
        response = "📋 **Cotizaciones Recientes**\n\n"
        for i, cot in enumerate(cotizaciones[:3], 1):
            numero = cot.get('numero_cotizacion', 'N/A')
            destino = cot.get('destino', 'Sin destino')
            total = cot.get('total_cotizado', 0)
            estado = cot.get('estado', 'Sin estado')
            response += f"{i}. #{numero} - {destino} - ${total:,.2f} ({estado})\n"
        
        response += "\n¿Necesitas ayuda con alguna cotización específica?"
        return response
    
    def _handle_clients_query(self, data):
        clientes = data.get('clientes_nuevos', [])
        
        if not clientes:
            return "👥 **Clientes**\n\nNo tienes clientes nuevos registrados en los últimos 30 días.\n\n¿Te gustaría revisar tu base de clientes existente?"
        
        response = "👥 **Clientes Nuevos (últimos 30 días)**\n\n"
        for i, cliente in enumerate(clientes[:5], 1):
            nombre = cliente.get('nombre', 'Sin nombre')
            apellido = cliente.get('apellido', '')
            email = cliente.get('email', 'Sin email')
            response += f"{i}. {nombre} {apellido} - {email}\n"
        
        response += "\n¿Quieres que te ayude a hacer seguimiento a algún cliente?"
        return response
    
    def _handle_summary_query(self, data):
        ventas_mes = data.get('ventas_este_mes', {'total': 0, 'cantidad': 0})
        pendientes = data.get('pendientes_pago', {'total': 0, 'cantidad': 0})
        
        return f"""🎯 **Resumen Ejecutivo - TravelHub**

**💼 Ventas este mes:**
• ${ventas_mes['total']:,.2f} en {ventas_mes['cantidad']} ventas

**💰 Por cobrar:**
• ${pendientes['total']:,.2f} pendientes

**📊 Estado general:**
{self._get_business_insight(data)}

¿En qué área específica te gustaría profundizar?"""
    
    def _handle_general_query(self, data):
        return """¡Hola! 👋 Soy tu Agente Inteligente de TravelHub.

Puedo ayudarte con:
• 📊 Consultar ventas y estadísticas
• 💰 Revisar pagos pendientes
• 📋 Gestionar cotizaciones
• 👥 Información de clientes
• 🎯 Resumen ejecutivo

¿Qué te gustaría saber?"""
    
    def _get_business_insight(self, data):
        ventas_mes = data.get('ventas_este_mes', {}).get('total', 0)
        pendientes = data.get('pendientes_pago', {}).get('total', 0)
        
        if pendientes == 0:
            return "✅ Excelente flujo de caja - sin pendientes"
        elif ventas_mes == 0:
            return "🟡 Sin ventas este mes"
        elif pendientes < ventas_mes * 0.2:
            return "🟢 Buen control de cobranza"
        elif pendientes < ventas_mes * 0.5:
            return "🟡 Revisar seguimiento de pagos"
        else:
            return "🔴 Priorizar cobranza - alto nivel de pendientes"
    
    def _get_system_data(self):
        """Obtiene datos actuales del sistema"""
        now = timezone.now()
        mes_actual = now.replace(day=1)
        hace_30_dias = now - timedelta(days=30)
        
        try:
            # Estadísticas de ventas
            ventas_mes = Venta.objects.filter(fecha_venta__gte=mes_actual).aggregate(
                total=Sum('total_venta'),
                count=Count('id_venta')
            )
            
            ventas_30d = Venta.objects.filter(fecha_venta__gte=hace_30_dias).aggregate(
                total=Sum('total_venta'),
                count=Count('id_venta')
            )
            
            # Ventas pendientes de pago
            pendientes = Venta.objects.filter(
                Q(estado='PEN') | Q(estado='PAR')
            ).aggregate(
                total=Sum('saldo_pendiente'),
                count=Count('id_venta')
            )
            
            # Cotizaciones recientes
            cotizaciones = list(Cotizacion.objects.filter(
                fecha_emision__gte=hace_30_dias
            ).values(
                'numero_cotizacion', 'estado', 'total_cotizado', 'destino'
            )[:5])
            
            # Clientes recientes
            clientes_recientes = list(PersonaCliente.objects.filter(
                fecha_registro__gte=hace_30_dias
            ).values('nombre', 'apellido', 'email')[:5])
            
            return {
                'fecha_actual': now.strftime('%Y-%m-%d %H:%M'),
                'ventas_este_mes': {
                    'total': float(ventas_mes['total'] or 0),
                    'cantidad': ventas_mes['count']
                },
                'ventas_ultimos_30d': {
                    'total': float(ventas_30d['total'] or 0),
                    'cantidad': ventas_30d['count']
                },
                'pendientes_pago': {
                    'total': float(pendientes['total'] or 0),
                    'cantidad': pendientes['count']
                },
                'cotizaciones_recientes': cotizaciones,
                'clientes_nuevos': clientes_recientes
            }
            
        except Exception as e:
            return {'error': f'Error obteniendo datos: {str(e)}'}

# Instancia global del agente
agent = TravelHubAgent()
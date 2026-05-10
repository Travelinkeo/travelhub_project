import json
import logging
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings

from apps.bookings.models import Venta, ItemVenta, Proveedor
from apps.finance.models import Factura
from apps.crm.models import Cliente
from apps.cotizaciones.models import Cotizacion
from apps.cms.models import Articulo, GuiaDestino
from apps.finance.models.core_finance import GastoOperativo
from apps.finance.models.reconciliacion import ReporteReconciliacion, LineaReporteReconciliacion, ConciliacionBoleto
from apps.contabilidad.reportes import ReportesContables
from apps.finance.models.currencies import Moneda
from apps.contabilidad.models import PlanContable, AsientoContable, DetalleAsiento
from apps.marketing.services.copywriter_service import CopywriterService

from core.middleware import get_current_agency

logger = logging.getLogger(__name__)

class AgentTools:
    """
    Colección de herramientas (funciones) que el Agente IA puede ejecutar
    para obtener datos reales del ERP.
    """

    @staticmethod
    def get_sales_stats(days: int = 30) -> str:
        """
        Obtiene estadísticas de ventas para los últimos N días de la agencia actual.
        """
        try:
            agencia = get_current_agency()
            if not agencia:
                return "Error: No hay una agencia en el contexto actual."
                
            since = timezone.now() - timedelta(days=days)
            stats = Venta.objects.filter(agencia=agencia, fecha_venta__gte=since).aggregate(
                total=Sum('total_venta'),
                cantidad=Count('id_venta'),
                utilidad=Sum('utilidad_estimada')
            )
            
            result = {
                "periodo_dias": days,
                "total_ventas": float(stats['total'] or 0),
                "cantidad_operaciones": stats['cantidad'],
                "utilidad_estimada": float(stats['utilidad'] or 0),
                "moneda": "USD",
                "agencia": agencia.nombre
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error obteniendo ventas: {str(e)}"

    @staticmethod
    def get_financial_kpis() -> str:
        """
        Obtiene indicadores clave: Ventas operativas, gastos del mes y utilidad neta contable.
        """
        try:
            agencia = get_current_agency()
            if not agencia: return "Error: Agencia no detectada."
            
            primer_dia_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            hoy = timezone.now().date()
            
            # 1. Datos Operativos (Ventas y Gastos cargados)
            ventas_op = Venta.objects.filter(agencia=agencia, fecha_venta__gte=primer_dia_mes)
            total_ventas = ventas_op.aggregate(s=Sum('total_venta'))['s'] or 0
            
            gastos_op = GastoOperativo.objects.filter(agencia=agencia, fecha_gasto__gte=primer_dia_mes.date())
            total_gastos = gastos_op.aggregate(s=Sum('monto'))['s'] or 0
            
            # 2. Datos Contables Reales (P&L del mes)
            res_contable = ReportesContables.estado_resultados(primer_dia_mes.date(), hoy)
            
            result = {
                "periodo": primer_dia_mes.strftime("%B %Y"),
                "vista_operativa": {
                    "ventas_totales": float(total_ventas),
                    "gastos_registrados": float(total_gastos),
                    "utilidad_operativa": float(total_ventas - total_gastos)
                },
                "vista_contable": {
                    "ingresos_reales": float(res_contable['ingresos']),
                    "gastos_reales": float(res_contable['gastos']),
                    "utilidad_neta": float(res_contable['utilidad_neta'])
                },
                "moneda": "USD"
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error en KPIs: {str(e)}"

    @staticmethod
    def get_pending_payments() -> str:
        """
        Lista las facturas o ventas que tienen saldo pendiente por cobrar.
        """
        try:
            agencia = get_current_agency()
            ventas = Venta.objects.filter(
                agencia=agencia,
                estado__in=['PEN', 'PAR']
            ).order_by('-fecha_venta')[:10]
            
            pendientes = []
            for v in ventas:
                pendientes.append({
                    "localizador": v.localizador,
                    "cliente": str(v.cliente),
                    "total": float(v.total_venta),
                    "saldo_pendiente": float(v.saldo_pendiente),
                    "fecha": v.fecha_venta.strftime('%Y-%m-%d')
                })
            
            total_pendiente = sum(p['saldo_pendiente'] for p in pendientes)
            
            return json.dumps({
                "total_por_cobrar": total_pendiente,
                "detalles": pendientes
            }, indent=2)
        except Exception as e:
            return f"Error obteniendo pendientes: {str(e)}"

    @staticmethod
    def get_financial_report(report_type: str, date_from: str, date_to: str) -> str:
        """
        Genera un reporte financiero (balance, estado_resultados).
        report_type: 'balance_general', 'estado_resultados', 'balance_comprobacion'
        date_from/date_to: formato YYYY-MM-DD
        """
        try:
            d_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            d_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            if report_type == 'estado_resultados':
                data = ReportesContables.estado_resultados(d_from, d_to)
            elif report_type == 'balance_comprobacion':
                data = ReportesContables.balance_comprobacion(d_from, d_to)
            elif report_type == 'balance_general':
                # Balance general solo usa una fecha de corte
                data = ReportesContables.balance_general(d_to)
            else:
                return "Tipo de reporte no válido."

            # Convertir Decimal a float para JSON
            def decimal_default(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                if isinstance(obj, (date, datetime)):
                    return obj.isoformat()
                raise TypeError
                
            return json.dumps(data, default=decimal_default, indent=2)
        except Exception as e:
            return f"Error en reporte contable: {str(e)}"

    @staticmethod
    def get_client_info(query: str) -> str:
        """
        Busca información de un cliente por nombre o ID.
        """
        try:
            clientes = Cliente.objects.filter(
                Q(nombre__icontains=query) | 
                Q(apellido__icontains=query) | 
                Q(numero_identificacion__icontains=query)
            )[:5]
            
            results = []
            for c in clientes:
                results.append({
                    "id": c.id_persona,
                    "nombre_completo": f"{c.nombre} {c.apellido}",
                    "identificacion": c.numero_identificacion,
                    "email": c.email,
                    "telefono": c.telefono_movil
                })
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error buscando cliente: {str(e)}"

    @staticmethod
    def get_quote_status(pnr: str) -> str:
        """
        Verifica el estado de una cotización o reserva por PNR/Localizador.
        """
        try:
            item = ItemVenta.objects.filter(codigo_reserva_proveedor__iexact=pnr).first()
            if not item:
                return f"No se encontró ninguna reserva con el localizador {pnr}."
            
            return json.dumps({
                "pnr": pnr,
                "tipo": item.get_tipo_producto_display(),
                "estado": item.venta.get_estado_display(),
                "cliente": str(item.venta.cliente),
                "pasajeros": item.pasajeros_nombres
            }, indent=2)
        except Exception as e:
            return f"Error buscando PNR: {str(e)}"

    @staticmethod
    def get_recent_expenses(limit: int = 10) -> str:
        """
        Consulta los gastos operativos más recientes de la agencia.
        """
        try:
            agencia = get_current_agency()
            gastos = GastoOperativo.objects.filter(agencia=agencia).order_by('-fecha_gasto')[:limit]
            
            results = []
            for g in gastos:
                results.append({
                    "id": g.id_gasto,
                    "descripcion": g.descripcion,
                    "monto": float(g.monto),
                    "moneda": g.moneda.codigo_iso,
                    "categoria": g.categoria.nombre if g.categoria else "General",
                    "fecha": g.fecha_gasto.strftime('%Y-%m-%d'),
                    "estado": g.get_estado_pago_display()
                })
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error obteniendo gastos: {str(e)}"

    @staticmethod
    def generate_cms_content(title: str, destination: str, content: str, content_type: str = 'articulo') -> str:
        """
        Guarda contenido generado para el CMS (Blog o Guía de Viaje).
        title: Título del artículo o nombre del destino.
        destination: Destino relacionado.
        content: El contenido completo (Markdown).
        content_type: 'articulo' o 'guia'
        """
        try:
            if content_type == 'articulo':
                obj = Articulo.objects.create(
                    titulo=title,
                    slug=title.lower().replace(' ', '-'),
                    destino=destination,
                    contenido=content,
                    generado_por_ia=True,
                    estado='BOR'
                )
                return f"Éxito: Se ha guardado el borrador del artículo '{title}' (ID: {obj.id})."
            else:
                obj = GuiaDestino.objects.create(
                    nombre=destination,
                    descripcion=content
                )
                return f"Éxito: Se ha guardado la guía del destino '{destination}' (ID: {obj.id})."
        except Exception as e:
            return f"Error guardando contenido CMS: {str(e)}"

    @staticmethod
    def list_cms_content(content_type: str = 'articulo') -> str:
        """
        Lista los artículos o guías existentes en el CMS.
        """
        try:
            if content_type == 'articulo':
                items = Articulo.objects.all().order_by('-fecha_creacion')[:10]
                results = [{"id": i.id, "titulo": i.titulo, "estado": i.get_estado_display()} for i in items]
            else:
                items = GuiaDestino.objects.all()[:10]
                results = [{"id": i.id, "nombre": i.nombre} for i in items]
            
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error listando CMS: {str(e)}"

    @staticmethod
    def get_reconciliation_summary(report_id: Optional[int] = None) -> str:
        """
        Obtiene un resumen del último reporte de conciliación de proveedores o uno específico.
        """
        try:
            agencia = get_current_agency()
            if report_id:
                report = ReporteProveedor.objects.filter(agencia=agencia, id=report_id).first()
            else:
                report = ReporteProveedor.objects.filter(agencia=agencia).order_by('-fecha_carga').first()
            
            if not report:
                return "No se encontraron reportes de conciliación."
            
            items = report.items.all()
            stats = {
                "proveedor": report.proveedor.nombre,
                "fecha": report.fecha_carga.strftime('%Y-%m-%d'),
                "total_items": items.count(),
                "coincidencias_ok": items.filter(estado='MAT').count(),
                "discrepancias": items.filter(estado='DIS').count(),
                "faltantes_en_sistema": items.filter(estado='MIN').count(),
                "notas": report.notas
            }
            
            discrepancias = []
            for item in items.filter(estado='DIS')[:5]:
                discrepancias.append({
                    "boleto": item.numero_boleto,
                    "monto_proveedor": float(item.monto_total_proveedor),
                    "monto_sistema": float(item.monto_sistema),
                    "diferencia": float(item.monto_total_proveedor - item.monto_sistema)
                })
            
            stats["top_discrepancias"] = discrepancias
            return json.dumps(stats, indent=2)
        except Exception as e:
            return f"Error obteniendo resumen de conciliación: {str(e)}"

    @staticmethod
    def get_cash_flow_summary(days: int = 30) -> str:
        """
        Resumen de flujo de caja (Ingresos vs Egresos) de los últimos N días.
        """
        try:
            agencia = get_current_agency()
            since = timezone.now() - timedelta(days=days)
            ingresos = Factura.objects.filter(agencia=agencia, fecha_emision__gte=since, estado='PAG').aggregate(total=Sum('monto_total'))['total'] or 0
            egresos = GastoOperativo.objects.filter(agencia=agencia, fecha_gasto__gte=since).aggregate(total=Sum('monto'))['total'] or 0
            
            return json.dumps({
                "periodo_dias": days,
                "ingresos_facturados_pagados": float(ingresos),
                "egresos_operativos": float(egresos),
                "flujo_neto_estimado": float(ingresos - egresos),
                "moneda": "USD"
            }, indent=2)
        except Exception as e:
            return f"Error en flujo de caja: {e}"

    

    @staticmethod
    def generate_marketing_copy(hotel_id: int, tone: str = "LUXURY") -> str:
        """
        Genera un paquete de marketing especializado (hashtags, captions, variantes) para un hotel.
        """
        try:
            service = CopywriterService()
            package = service.generate_social_package(hotel_id, tone)
            
            if "error" in package:
                return f"Error de IA: {package['error']}"
                
            return json.dumps(package, indent=2)
        except Exception as e:
            return f"Error generando marketing: {str(e)}"

    @staticmethod
    def get_account_balance(codigo_cuenta: str) -> str:
        """Consulta detalles y saldo actual de una cuenta del Plan Contable."""
        try:
            agencia = get_current_agency()
            cuenta = PlanContable.objects.get(agencia=agencia, codigo_cuenta=codigo_cuenta)
            
            # Calcular saldo desde el mayor acumulado
            movimientos = DetalleAsiento.objects.filter(
                cuenta_contable=cuenta,
                asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
            ).aggregate(
                debe=Sum('debe'),
                haber=Sum('haber')
            )
            
            debe = movimientos['debe'] or Decimal('0')
            haber = movimientos['haber'] or Decimal('0')
            
            # Naturaleza Deudora: Debe - Haber. Naturaleza Acreedora: Haber - Debe.
            if cuenta.naturaleza == 'D':
                saldo = debe - haber
            else:
                saldo = haber - debe
                
            return json.dumps({
                "nombre": cuenta.nombre_cuenta,
                "codigo": cuenta.codigo_cuenta,
                "naturaleza": cuenta.get_naturaleza_display(),
                "saldo_actual": float(saldo),
                "moneda": "USD",
                "detalles": {
                    "total_debe": float(debe),
                    "total_haber": float(haber)
                }
            }, indent=2)
        except PlanContable.DoesNotExist:
            return f"Error: La cuenta {codigo_cuenta} no existe en esta agencia."
        except Exception as e:
            return f"Error consultando cuenta: {str(e)}"

    @staticmethod
    def get_cashflow_forecast(dias: int = 30) -> str:
        """Predice el flujo de caja entrante basado en vencimientos de facturas."""
        try:
            agencia = get_current_agency()
            hoy = timezone.now().date()
            limite = hoy + timedelta(days=dias)
            
            facturas = Factura.objects.filter(
                agencia=agencia,
                estado__in=['EMI', 'PAR', 'VEN'],
                saldo_pendiente__gt=0,
                fecha_vencimiento__lte=limite
            ).values('fecha_vencimiento', 'moneda__codigo_iso').annotate(
                total=Sum('saldo_pendiente')
            ).order_by('fecha_vencimiento')
            
            forecast = []
            for f in facturas:
                forecast.append({
                    "fecha": f['fecha_vencimiento'].strftime("%Y-%m-%d"),
                    "monto": float(f['total']),
                    "moneda": f['moneda__codigo_iso']
                })
                
            return json.dumps({
                "periodo_proyectado": f"{dias} días",
                "total_proyectado_usd": sum(f['monto'] for f in forecast if f['moneda'] == 'USD'),
                "detalles": forecast
            }, indent=2)
        except Exception as e:
            return f"Error en forecast: {str(e)}"

    @staticmethod
    def get_reconciliation_discrepancies(numero_boleto: str) -> str:
        """Analiza discrepancias específicas para un boleto en los reportes de reconciliación."""
        try:
            agencia = get_current_agency()
            # Buscar en el nuevo modelo de conciliación
            c = ConciliacionBoleto.objects.filter(
                agencia=agencia, 
                linea_reporte__numero_boleto_reportado=numero_boleto
            ).first()
            
            if not c: 
                # Intentar buscar por el boleto local si no match por reporte
                c = ConciliacionBoleto.objects.filter(
                    agencia=agencia, 
                    boleto_local__numero_boleto=numero_boleto
                ).first()
                
            if not c:
                return f"Boleto {numero_boleto} no encontrado en procesos de reconciliación."
            
            return json.dumps({
                "boleto": numero_boleto,
                "estado": c.get_estado_display(),
                "diferencia_total": float(c.diferencia_total),
                "desglose": {
                    "dif_tarifa": float(c.diferencia_tarifa),
                    "dif_impuestos": float(c.diferencia_impuestos)
                },
                "ia_razonamiento": c.ia_razonamiento or "No disponible"
            }, indent=2)
        except Exception as e:
            return f"Error analizando discrepancia: {str(e)}"

    @staticmethod
    def run_reconciliation(report_id: str) -> str:
        """
        Inicia el proceso de reconciliación automática para un reporte ya subido.
        report_id: El UUID del reporte.
        """
        try:
            from apps.finance.services.smart_reconciliation_service import SmartReconciliationService
            # Ejecutar de forma síncrona (el agente esperará la respuesta)
            # NOTA: En producción esto debería ser una tarea de Celery, 
            # pero para el agente IA solemos querer feedback inmediato o confirmación de inicio.
            SmartReconciliationService.procesar_reporte(report_id)
            return f"Éxito: Se ha procesado la reconciliación para el reporte {report_id}. Usa 'get_reconciliation_summary' para ver los resultados."
        except Exception as e:
            return f"Error ejecutando reconciliación: {str(e)}"

import json
import logging
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.services.ai_parser_service import AIParserService
from core.ticket_parser import extract_data_from_text
from apps.bookings.models import Venta, BoletoImportado, ItemVenta
from core.models import Moneda, Proveedor
from core.models.notificaciones import NotificacionInteligente
from apps.crm.models import Cliente
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ResendInboundWebhookView(View):
    """
    🎯 THE INVISIBLE AGENT
    Este webhook recibe correos de boletos, los procesa y crea ventas automáticamente.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            subject = data.get('subject', 'Sin asunto')
            from_email = data.get('from', {}).get('email', 'desconocido')
            text_body = data.get('text', '')
            html_body = data.get('html', '')
            
            logger.info(f"📧 Correo entrante detectado: {subject} desde {from_email}")
            
            # 1. ANALIZAR CON IA (God Mode)
            parsed_data = AIParserService.parse_text(text_body or html_body)
            
            if not parsed_data or "error" in parsed_data:
                logger.warning(f"⚠️ No se pudo extraer información del correo {subject}")
                return JsonResponse({"status": "error", "message": "No airline data found"}, status=200)
            
            # 2. PROCESAR VENTA (Automatic Creation)
            # Buscamos un usuario (consultor) por el correo de origen para asignar la agencia
            consultor = User.objects.filter(email=from_email).first() or User.objects.filter(is_superuser=True).first()
            
            # Moneda base
            moneda_base = Moneda.objects.get(codigo_iso='USD')
            
            # Obtener datos de pasajeros
            boletos_list = parsed_data.get("boletos", [])
            for b_data in boletos_list:
                pnr = b_data.get("codigo_reserva")
                nombre_pax = b_data.get("nombre_pasajero")
                total = float(b_data.get("total", 0.0))
                
                # Crear Venta
                venta = Venta.objects.create(
                    consultor=consultor,
                    agencia=consultor.agencias.filter(activo=True).first().agencia if hasattr(consultor, 'agencias') else None,
                    localizador=pnr,
                    estado='PEN', # Pendiente de pago/validar
                    moneda=moneda_base,
                    total_venta=total
                )
                
                # Crear Boleto
                itinerario = b_data.get("itinerario", [])
                ruta = " - ".join([f"{v.get('origen')}->{v.get('destino')}" for v in itinerario])
                
                BoletoImportado.objects.create(
                    venta_asociada=venta,
                    numero_boleto=b_data.get("numero_boleto"),
                    pasajero_nombre_completo=nombre_pax,
                    localizador_pnr=pnr,
                    aerolinea=b_data.get("nombre_aerolinea"),
                    ruta=ruta[:255]
                )
                
                # 🔔 NOTIFICAR AL CONSULTOR (Magic Toast)
                NotificacionInteligente.objects.create(
                    usuario=consultor,
                    tipo='ai_magic',
                    titulo='🎯 Agente Invisible: Boleto Procesado',
                    mensaje=f'He procesado automáticamente un boleto para {nombre_pax} (PNR: {pnr}). La venta y factura están listas.',
                    ahorro_tiempo='15 min'
                )
                
                # 🧾 AUTO-FACTURACIÓN: Crear borrador de factura
                try:
                    # Importación diferida para evitar bloqueos / dependencias circulares al arrancar Django
                    from apps.finance.models.core_finance import Factura, ItemFactura
                    from decimal import Decimal
                    
                    factura = Factura.objects.create(
                        venta_asociada=venta,
                        agencia=consultor.agencias.filter(activo=True).first().agencia if hasattr(consultor, 'agencias') else None,
                        cliente=None, # Asignar después o dejar null si es genérico
                        moneda=moneda_base,
                        tasa_cambio=Decimal(1.0),
                        estado=Factura.EstadoFactura.BORRADOR,
                        tipo_factura=Factura.TipoFactura.TERCEROS,
                        notas=f"Generada automáticamente por Invisible Agent - PNR: {pnr}"
                    )
                    
                    # Crear el item maestro de la factura (boleto)
                    desc = f"Boleto Aéreo: {b_data.get('nombre_aerolinea')} - {ruta}"
                    ItemFactura.objects.create(
                        factura=factura,
                        descripcion=desc[:500],
                        cantidad=Decimal(1),
                        precio_unitario=Decimal(total),
                        tipo_impuesto='00' # Exento por defecto
                    )
                    
                    factura.recalcular_totales()
                    factura.save()
                    logger.info(f"🧾 Factura {factura.numero_factura} creada automáticamente.")
                except Exception as e:
                    logger.error(f"Error en auto-facturación: {str(e)}")

                logger.info(f"✅ Venta {venta.id_venta} creada automáticamente para {nombre_pax}")
            
            return JsonResponse({"status": "success", "message": "Booking processed automatically"})
            
        except Exception as e:
            logger.error(f"🔥 Error procesando webhook de Resend: {str(e)}")
            return HttpResponse(status=500)

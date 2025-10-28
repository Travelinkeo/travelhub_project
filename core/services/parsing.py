# Archivo: core/services/parsing.py

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.base import ContentFile

from core.models.boletos import BoletoImportado
from .ticket_parser_service import orquestar_parseo_de_boleto
from core import ticket_parser # Importar para generar PDF

logger = logging.getLogger(__name__)

def procesar_boleto_importado_automatico(boleto: BoletoImportado):
    """
    Lógica de negocio para parsear un boleto, rellenar los campos del modelo
    y generar el PDF automáticamente.
    """
    logger.info(f"Iniciando procesamiento automático para Boleto ID: {boleto.id_boleto_importado}")
    
    campos_a_actualizar = ['datos_parseados', 'estado_parseo', 'log_parseo']

    try:
        if not boleto.archivo_boleto:
            raise ValueError("No hay ningún archivo de boleto para procesar.")

        boleto.estado_parseo = BoletoImportado.EstadoParseo.EN_PROCESO
        boleto.save(update_fields=['estado_parseo'])

        datos_parseados, mensaje = orquestar_parseo_de_boleto(boleto.archivo_boleto)

        if not datos_parseados:
            raise Exception(f"Fallo en el parseo: {mensaje}")

        # --- 1. Mapear JSON a los campos del modelo ---
        boleto.datos_parseados = datos_parseados
        
        source_system = datos_parseados.get('SOURCE_SYSTEM')

        if source_system == 'KIU':
            boleto.numero_boleto = datos_parseados.get('NUMERO_DE_BOLETO')
            boleto.nombre_pasajero_completo = datos_parseados.get('NOMBRE_DEL_PASAJERO')
            boleto.nombre_pasajero_procesado = datos_parseados.get('SOLO_NOMBRE_PASAJERO')
            boleto.localizador_pnr = datos_parseados.get('SOLO_CODIGO_RESERVA')
            boleto.aerolinea_emisora = datos_parseados.get('NOMBRE_AEROLINEA')
            boleto.total_boleto = datos_parseados.get('TOTAL_IMPORTE')
            boleto.tarifa_base = datos_parseados.get('TARIFA_IMPORTE')
            boleto.foid_pasajero = datos_parseados.get('CODIGO_IDENTIFICACION')
            boleto.ruta_vuelo = datos_parseados.get('ItinerarioFinalLimpio')
            # Asegurarse de que todos los campos relevantes se añaden para ser guardados
            campos_a_actualizar.extend([
                'numero_boleto', 'nombre_pasajero_completo', 'nombre_pasajero_procesado', 
                'localizador_pnr', 'aerolinea_emisora', 'total_boleto', 'tarifa_base', 'foid_pasajero', 'ruta_vuelo'
            ])
        else: # Asumir Sabre u otra estructura anidada
            reserva = datos_parseados.get("reserva", {})
            pasajero = datos_parseados.get("pasajero", {})
            
            boleto.numero_boleto = reserva.get("numero_boleto")
            boleto.nombre_pasajero_completo = pasajero.get("nombre_completo")
            boleto.nombre_pasajero_procesado = pasajero.get("nombre_completo", "").split('/')[1] if '/' in pasajero.get("nombre_completo", "") else pasajero.get("nombre_completo")
            boleto.localizador_pnr = reserva.get("codigo_reservacion")
            boleto.aerolinea_emisora = reserva.get("aerolinea_emisora")
            # Aquí también se deberían mapear los campos monetarios si existen para Sabre
            # ej: boleto.total_boleto = reserva.get('total_amount')
            
            campos_a_actualizar.extend([
                'numero_boleto', 'nombre_pasajero_completo', 'nombre_pasajero_procesado', 
                'localizador_pnr', 'aerolinea_emisora'
            ])

        boleto.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO
        boleto.log_parseo = f"Parseo automático completado. Mensaje: {mensaje}"

        # --- 2. Generar y guardar el PDF ---
        try:
            pdf_bytes, pdf_filename = ticket_parser.generate_ticket(datos_parseados)
            if pdf_bytes:
                # Usamos save=False para evitar un bucle en la señal post_save
                boleto.archivo_pdf_generado.save(pdf_filename, ContentFile(pdf_bytes), save=False)
                campos_a_actualizar.append('archivo_pdf_generado')
                logger.info(f"PDF '{pdf_filename}' generado para el boleto {boleto.id_boleto_importado}.")
        except Exception as pdf_e:
            logger.error(f"Error generando PDF para boleto {boleto.id_boleto_importado}: {pdf_e}")
            boleto.log_parseo += f" | ADVERTENCIA: No se pudo generar el PDF: {pdf_e}"

    except Exception as e:
        logger.error(f"Error procesando boleto ID {boleto.id_boleto_importado}: {e}", exc_info=True)
        boleto.estado_parseo = BoletoImportado.EstadoParseo.ERROR_PARSEO
        boleto.datos_parseados = {'error': str(e)}
        boleto.log_parseo = f"Error GRAVE durante el parseo automático: {e}"
    
    finally:
        # Guardar todos los campos actualizados de una sola vez
        boleto.save(update_fields=campos_a_actualizar)

@receiver(post_save, sender=BoletoImportado)
def trigger_boleto_parse_service(sender, instance, created, **kwargs):
    """
    Disparador que se activa al crear un nuevo BoletoImportado.
    Solo procesa si hay archivo adjunto (no entrada manual).
    """
    # Evitar que se ejecute en bucle si la función de procesamiento guarda el mismo objeto
    if created and instance.estado_parseo == BoletoImportado.EstadoParseo.PENDIENTE and instance.archivo_boleto:
        logger.info(f"Disparador automático: Invocando servicio de parseo para nuevo boleto ID {instance.id_boleto_importado}")
        procesar_boleto_importado_automatico(instance)
    elif created and not instance.archivo_boleto:
        logger.info(f"Boleto ID {instance.id_boleto_importado} creado manualmente sin archivo. Se omite parseo automático.")
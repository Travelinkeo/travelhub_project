import logging
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

# Importaciones asumidas basadas en la arquitectura del proyecto
# Asegúrate de ajustar las rutas de importación a la estructura exacta de tus apps
from apps.bookings.models import BoletoImportado 
from apps.automation.services.ticket_parser_service import TicketParserService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, queue='ia_fast', soft_time_limit=20, time_limit=30)
def process_web_uploaded_ticket(self, boleto_id):
    """
    Procesa un boleto subido manualmente por la web.
    BLINDADO contra Estados Huérfanos: Siempre actualiza la DB en caso de fallo.
    """
    # ENVOLTURA GLOBAL: Previene que cualquier error deje la base de datos en estado 'Procesando'
    try:
        # 1. Recuperar el boleto de la base de datos usando pk (id_boleto_importado)
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        
        # Opcional: Asegurar que el estado esté en proceso al iniciar
        if boleto.estado_parseo != BoletoImportado.EstadoParseo.EN_PROCESO:
            boleto.estado_parseo = BoletoImportado.EstadoParseo.EN_PROCESO
            boleto.save(update_fields=['estado_parseo'])

        logger.info(f"Iniciando procesamiento de boleto web ID: {boleto_id}")

        # 2. Inicializar el servicio de parseo y ejecutar la extracción
        parser_service = TicketParserService()
        
        # Ejecutamos la lógica principal del parser (esto llamará a Gemini y hará el fallback si es necesario)
        resultado = parser_service.procesar_boleto(boleto_id=boleto_id)

        # 3. VERIFICACIÓN DE DICCIONARIO CON ERRORES (Punto 5 del diagnóstico)
        # Si el servicio no explotó (no lanzó excepción) pero devolvió un error lógico controlado
        if isinstance(resultado, dict) and "error" in resultado:
            logger.error(f"Error lógico devuelto por el parser para el boleto {boleto_id}: {resultado['error']}")
            
            # Recargar de base de datos
            boleto.refresh_from_db()
            # OBLIGATORIO: Actualizar el estado a revisión manual
            boleto.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
            
            # Acumular el log del error
            log_previo = boleto.log_parseo + " | " if boleto.log_parseo else ""
            boleto.log_parseo = f"{log_previo}Error en extracción: {resultado['error']}"
            boleto.save()
            
            return f"Finalizado con error lógico: {resultado['error']}"

        # 4. Finalización exitosa
        # Recargar para verificar el estado final
        boleto.refresh_from_db()
        if boleto.estado_parseo == BoletoImportado.EstadoParseo.EN_PROCESO:
            boleto.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO
            boleto.save()
        
        logger.info(f"Boleto {boleto_id} procesado y guardado exitosamente.")
        return "Procesamiento Exitoso"

    except SoftTimeLimitExceeded:
        # CAPTURA DE TIMEOUT (Punto 4)
        logger.error(f"❌ SoftTimeLimitExceeded: La IA tardó demasiado procesando el boleto {boleto_id}.")
        try:
            # Buscamos el boleto nuevamente en caso de que la variable local esté corrupta
            boleto_fallido = BoletoImportado.objects.get(pk=boleto_id)
            boleto_fallido.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
            
            log_previo = boleto_fallido.log_parseo + " | " if boleto_fallido.log_parseo else ""
            boleto_fallido.log_parseo = f"{log_previo}CRITICAL: Timeout de IA (SoftTimeLimit superado)."
            boleto_fallido.save()
        except Exception as db_error:
            logger.critical(f"Fallo al intentar guardar el estado de timeout para boleto {boleto_id}: {db_error}")
            
        return "Abortado por Timeout"

    except Exception as e:
        # CAPTURA DE CUALQUIER OTRA EXCEPCIÓN GLOBAL (Punto 4)
        logger.error(f"❌ Excepción fatal procesando el boleto {boleto_id}: {str(e)}", exc_info=True)
        try:
            # Recuperar y blindar el estado final
            boleto_fallido = BoletoImportado.objects.get(pk=boleto_id)
            boleto_fallido.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
            
            log_previo = boleto_fallido.log_parseo + " | " if boleto_fallido.log_parseo else ""
            boleto_fallido.log_parseo = f"{log_previo}CRASH SISTEMA: {str(e)}"
            boleto_fallido.save()
        except Exception as db_error:
            logger.critical(f"Fallo al intentar guardar el estado de crash para boleto {boleto_id}: {db_error}")

        # Levantamos la excepción para que herramientas de monitoreo (como Sentry) la registren
        raise e
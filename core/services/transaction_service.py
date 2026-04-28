import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.bookings.models import Venta, ItemVenta
# Note: Adding placeholders for external providers as suggested in the manifesto
# from core.services.ticket_parser_service import ... 

logger = logging.getLogger(__name__)

class TransactionService:
    """
    Servicio de Integridad Transaccional (Doctrina ACID).
    Asegura que las operaciones financieras y de emisión sean atómicas y seguras.
    """

    @staticmethod
    def procesar_pago_y_emision(venta_id, datos_pago, funcion_emision_externa=None):
        """
        Ejecuta el cobro y la emisión en un bloque atómico con bloqueo de fila.
        Si la emisión externa falla, se revierte el estado del pago.
        """
        try:
            with transaction.atomic():
                # 1. Bloqueo de fila (Anti-concurrencia)
                # Evita que dos hilos procesen la misma venta simultáneamente.
                venta = Venta.objects.select_for_update().get(id_venta=venta_id)

                if venta.estado == Venta.EstadoVenta.COMPLETADA:
                    raise ValidationError("La venta ya ha sido completada.")

                # 2. Registro de Impacto Financiero
                # Aquí se integraría con el modelo de Pago o Factura
                # Por ahora, simulamos el cambio de estado.
                venta.estado = Venta.EstadoVenta.PAGADA_TOTAL
                venta.save()

                # 3. Punto de Fricción: Comunicación Externa
                # Si se proporciona una función de emisión (ej. KIU/Sabre), se ejecuta.
                if funcion_emision_externa:
                    resultado_externo = funcion_emision_externa(venta)
                    
                    if not resultado_externo.get('success'):
                        # Si el proveedor falla, lanzamos excepción para disparar el ROLLBACK
                        error_msg = resultado_externo.get('error', 'Error desconocido en proveedor externo')
                        raise Exception(f"Falla en proveedor externo: {error_msg}")

                # 4. Confirmación del Objetivo
                venta.estado = Venta.EstadoVenta.COMPLETADA
                venta.save()

                logger.info(f"Venta {venta_id} procesada exitosamente con integridad ACID.")
                return True, "Operación exitosa."

        except ValidationError as e:
            logger.warning(f"Validación fallida para venta {venta_id}: {str(e)}")
            return False, str(e)
        except Exception as e:
            # El bloque transaction.atomic() asegura el ROLLBACK automático aquí.
            logger.error(f"FALLO CRÍTICO en transacción de venta {venta_id}: {str(e)}")
            # En un entorno real, aquí se notificaría a Sentry o un log de auditoría.
            return False, f"Fallo en la operación. Los datos han sido revertidos. error: {str(e)}"

    @staticmethod
    def ejecutar_con_bloqueo(queryset, funcion, *args, **kwargs):
        """
        Utilidad genérica para ejecutar una función bajo un bloqueo select_for_update.
        """
        with transaction.atomic():
            locked_objects = queryset.select_for_update()
            return funcion(locked_objects, *args, **kwargs)

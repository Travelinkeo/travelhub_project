import logging

logger = logging.getLogger(__name__)


class VentaAutomationService:
    """
    Servicio centralizado para la automatización de lógica de negocio
    tras la importación de boletos y otros componentes.
    Delega en el motor unificado apps.automation.services.venta_automation.
    """

    @staticmethod
    def process_ticket_import(instance):
        """
        Crea o actualiza la Venta, Pasajero e Items a partir de un BoletoImportado
        utilizando el motor unificado de automatización de ventas.
        """
        if not instance or not instance.datos_parseados:
            return None

        from apps.automation.services.venta_automation import (
            VentaAutomationService as UnifiedVentaAutomation,
        )

        try:
            return UnifiedVentaAutomation.crear_venta_desde_parser(
                parsed_data=instance.datos_parseados,
                agencia=instance.agencia,
                usuario=None,
                boleto_obj=instance,
            )
        except Exception as e:
            logger.exception(f"❌ Error crítico en process_ticket_import: {str(e)}")
            return None

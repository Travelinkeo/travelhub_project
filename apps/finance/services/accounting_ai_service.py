import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.services.ai_engine import ai_engine
from apps.finance.models.ai_accounting_schemas import AsientoContableSchema
from core.prompts import ACCOUNTING_SYSTEM_PROMPT
from apps.contabilidad.models import AsientoContable, DetalleAsiento, PlanContable
from core.models_catalogos import Moneda

logger = logging.getLogger(__name__)

class AccountingAIService:
    """
    SERVICIO DE CONTABILIDAD IA (CPA ENGINE):
    Utiliza el razonamiento de Gemini para generar asientos contables 
    basados en descripciones de transacciones o hallazgos de conciliación.
    
    Este motor reemplaza miles de reglas estáticas por inteligencia financiera
    que entiende el catálogo de cuentas y los principios de partida doble.
    """

    @classmethod
    @transaction.atomic
    def generar_asiento_con_ia(cls, descripcion_transaccion: str, context_details: Optional[Dict] = None) -> Optional[AsientoContable]:
        """
        Interpreta una transacción y crea el asiento contable físico en TravelHub.
        
        Args:
            descripcion_transaccion: Texto natural describiendo el movimiento (ej: 'Venta de boleto PNR ABC123').
            context_details: Diccionario opcional con montos, fechas o IDs involucrados.
        """
        logger.info(f"🧠 Accounting AI: Generando asiento para: '{descripcion_transaccion[:80]}...'")

        # 1. Preparar el input enriquecido
        contexto_str = f"\nDATOS TÉCNICOS: {context_details}" if context_details else ""
        full_prompt = f"POR FAVOR, CONTABILIZA LA SIGUIENTE TRANSACCIÓN:\n{descripcion_transaccion}{contexto_str}"

        try:
            # 2. Invocación al Motor IA con Esquema de Partida Doble
            # Temperatura 0.0 para garantizar que la contabilidad sea determinística
            datos_asiento = ai_engine.call_gemini(
                prompt=full_prompt,
                response_schema=AsientoContableSchema,
                system_instruction=ACCOUNTING_SYSTEM_PROMPT,
                temperature=0.0
            )

            if not datos_asiento or not datos_asiento.get('lineas'):
                logger.error("El motor IA devolvió un asiento vacío o sin líneas.")
                return None

            # 3. Resolución de Moneda y Contexto
            iso_moneda = datos_asiento.get('moneda', 'USD')
            moneda = Moneda.objects.filter(codigo_iso=iso_moneda).first()
            if not moneda:
                moneda = Moneda.objects.get(codigo_iso='USD')

            # 4. CREACIÓN DEL ASIENTO (BORRADOR)
            asiento = AsientoContable.objects.create(
                descripcion_general=datos_asiento['descripcion_general'],
                fecha_contable=datos_asiento.get('fecha_contable', timezone.now().date()),
                moneda=moneda,
                tipo_asiento=AsientoContable.TipoAsiento.AJUSTE,
                estado=AsientoContable.EstadoAsiento.BORRADOR
            )

            # 5. PROCESAMIENTO DE LÍNEAS Y RESOLUCIÓN DE CUENTAS
            for i, l_schema in enumerate(datos_asiento['lineas'], 1):
                # Estrategia de búsqueda de cuenta: Código > Nombre Exacto > Similar
                cuenta = PlanContable.objects.filter(codigo_cuenta=l_schema['codigo_cuenta']).first()
                if not cuenta:
                    cuenta = PlanContable.objects.filter(nombre_cuenta__icontains=l_schema['nombre_cuenta']).first()
                
                if not cuenta:
                    error_msg = f"No se pudo localizar la cuenta contable: {l_schema['codigo_cuenta']} - {l_schema['nombre_cuenta']}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Persistir la línea de detalle
                DetalleAsiento.objects.create(
                    asiento=asiento,
                    linea=i,
                    cuenta_contable=cuenta,
                    debe=Decimal(str(round(l_schema['debe'], 2))),
                    haber=Decimal(str(round(l_schema['haber'], 2))),
                    descripcion_linea=l_schema['concepto']
                )

            # 6. Recalcular y validar cuadre final
            asiento.calcular_totales()
            
            if not asiento.esta_cuadrado:
                logger.error(f"⚠️ Asiento {asiento.id_asiento} generado descuadrado. Revirtiendo.")
                raise ValueError("El asiento generado por IA no cumple con la Partida Doble técnica.")

            logger.info(f"✅ Asiento Contable {asiento.id_asiento} creado exitosamente por CPA Engine.")
            return asiento

        except Exception as e:
            logger.exception(f"Fallo crítico en el motor de contabilidad IA: {e}")
            # El decorador transaction.atomic hará rollback automático si ocurre una excepción
            return None

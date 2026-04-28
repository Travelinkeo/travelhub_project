
import logging
from datetime import date
from decimal import Decimal
# 🛡️ RESILIENT INFRASTRUCTURE: pyDolarVenezuela v2.0+ support
from pyDolarVenezuela import Monitor
from pyDolarVenezuela.pages import BCV
# Import specific project services
from core.models_catalogos import TasaCambio 
from core.services.telegram_service import enviar_alerta_telegram

logger = logging.getLogger(__name__)

def obtener_tasa_bcv_resiliente(moneda: str = 'USD') -> float:
    """
    Motor de obtención de tasas con Fallback y Caché de Supervivencia.
    Utiliza pyDolarVenezuela para evadir bloqueos del gobierno.
    """
    hoy = date.today()
    moneda_iso = moneda.upper()
    
    # 1. INTENTO PRIMARIO: Consultar al BCV en vivo
    try:
        # Librería en v2.0+ usa Monitor(BCV)
        monitor = Monitor(BCV)
        monitores = monitor.get_all_monitors()
        
        # Mapeo de ISO a keys internas (minúsculas)
        target_key = moneda_iso.lower()
        
        monitor_data = None
        for m in monitores:
            m_key = m.get('key') if isinstance(m, dict) else getattr(m, 'key', None)
            if m_key == target_key:
                monitor_data = m
                break
        
        if monitor_data:
            # Extraer precio (limpiando de cualquier formato no decimal si fuera necesario)
            raw_price = monitor_data.get('price', 0) if isinstance(monitor_data, dict) else getattr(monitor_data, 'price', 0)
            tasa_float = float(str(raw_price))
            
            if tasa_float > 0:
                # Guardar o actualizar en nuestro Caché de Supervivencia
                TasaCambio.objects.update_or_create(
                    fecha=hoy,
                    moneda=moneda_iso,
                    defaults={'monto': Decimal(str(tasa_float))}
                )
                
                logger.info(f"✅ Tasa BCV obtenida en vivo: {tasa_float} {moneda_iso}")
                return tasa_float
        
        raise ValueError(f"Monitor {moneda_iso} no encontrado en la respuesta del BCV")
        
    except Exception as e:
        logger.warning(f"⚠️ Fallo al contactar al BCV (posible caída del servidor): {str(e)}")
        
        # 2. INTENTO SECUNDARIO (FALLBACK): Activar Caché de Supervivencia
        try:
            # Buscamos la última tasa válida registrada en la base de datos
            ultima_tasa = TasaCambio.objects.filter(moneda=moneda_iso).latest('fecha')
            
            logger.error(f"🛡️ BCV CAÍDO. Usando Caché de Supervivencia: {ultima_tasa.monto} del {ultima_tasa.fecha}")
            
            # Alerta silenciosa al Bot de Telegram de los dueños/administradores
            mensaje_alerta = (
                f"🚨 *ALERTA FINANCIERA - TRAVELHUB*\n\n"
                f"El portal del BCV no responde o cambió su estructura anti-bots.\n"
                f"🛡️ *Caché de Supervivencia Activado*.\n"
                f"Facturación temporal con la tasa más reciente: *{ultima_tasa.monto} Bs* ({ultima_tasa.fecha}).\n"
                f"Tus ventas no se han detenido."
            )
            enviar_alerta_telegram(mensaje_alerta)
            
            return float(ultima_tasa.monto)
            
        except TasaCambio.DoesNotExist:
            # Caso extremo: Base de datos vacía y BCV caído
            logger.critical("❌ BCV CAÍDO Y CACHÉ DE SUPERVIVENCIA VACÍO. ALTA GRAVEDAD.")
            return 0.0

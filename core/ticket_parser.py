import logging
import hashlib
from typing import Dict, Any, Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)

class FastDeterministicParsers:
    """
    🛡️ EL ESCUDO FINANCIERO (Fase 70% Determinístico)
    Aquí residirán tus parsers súper rápidos (Regex) que no consumen IA.
    Ahorra el 80% de los costos de Gemini si el boleto es conocido.
    """
    @staticmethod
    def parse_copa_standard(text: str) -> Optional[Dict]:
        # TODO: En el futuro, aquí pondremos un Regex rápido para Copa.
        # Por ahora retorna None para que el flujo pase a la IA (God Mode).
        return None

def extract_data_from_text(plain_text: str, html_text: str = "", pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Orquestador Híbrido (Decision Engine + Strategy Pipeline).
    1. Cache Aggressive (< 50ms, Cero Costo)
    2. Fast Regex (< 200ms, Cero Costo)
    3. Gemini God Mode Fallback (~3s, Costo API)
    """
    if not plain_text:
        return {"error": "Texto vacío"}

    # 1. 🧱 ESCUDO DE CACHÉ ABSOLUTO (Evita facturación doble por el mismo PDF)
    fingerprint = hashlib.sha256(plain_text.encode('utf-8')).hexdigest()
    cache_key = f"parser:doc:{fingerprint}"
    
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info("⚡ [CACHE HIT] Documento procesado en 0.05s sin tocar la IA.")
        return cached_result

    res_final = None

    # 2. ⚡ CLASIFICADOR Y ESTRATEGIA DETERMINÍSTICA (Cero Costo)
    # Si detectamos que es un texto predecible, intentamos extraerlo sin IA.
    if "COPA AIRLINES" in plain_text.upper() and "BOLETO" in plain_text.upper():
        res_final = FastDeterministicParsers.parse_copa_standard(plain_text)

    # 3. 🧠 FALLBACK DE INTELIGENCIA ARTIFICIAL (God Mode)
    if not res_final:
        logger.info("🧠 [AI ROUTING] Activando AIParserService para extracción inteligente...")
        try:
            from core.services.ai_parser_service import AIParserService
            res_final = AIParserService.parse_text(plain_text)
            
            if res_final and isinstance(res_final, dict) and "error" not in res_final:
                logger.info(f"✅ Éxito total con el nuevo AIParserService")
            else:
                error_msg = res_final.get('error') if isinstance(res_final, dict) else 'Sin datos útiles'
                logger.warning(f"⚠️ El nuevo motor IA devolvió: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ Fallo crítico en motor IA: {e}")
            res_final = {"error": f"Fallo en IA Universal: {str(e)}"}

    # 4. 💾 GUARDAR EN CACHÉ (Si fue exitoso, no volvemos a gastar tokens en este texto por 30 días)
    if res_final and "error" not in res_final:
        cache.set(cache_key, res_final, timeout=86400 * 30)

    return res_final


# ==========================================
# FUNCIONES UTILITARIAS (NO TOCAR)
# ==========================================
def is_brand_color_dark(hex_color: str) -> bool:
    """Detecta si un color es oscuro para ajustar el contraste del texto en los PDFs/Vouchers."""
    if not hex_color or not isinstance(hex_color, str):
        return True
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return True
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        return luma < 128
    except:
        return True

def _parse_date_robust(fecha_str: str):
    from core.parsing_utils import _formatear_fecha_dd_mm_yyyy, _fecha_a_iso
    import datetime
    res = _fecha_a_iso(_formatear_fecha_dd_mm_yyyy(fecha_str))
    if res:
        try:
            return datetime.datetime.strptime(res, '%Y-%m-%d').date()
        except:
             return None
    return None

def _get_solo_nombre_pasajero(nombre_completo: str) -> str:
    if not nombre_completo or nombre_completo == 'No encontrado':
        return nombre_completo
    if '/' in nombre_completo:
        parts = nombre_completo.split('/')
        if len(parts) > 1:
            return parts[1].split(' ')[0].strip()
    return nombre_completo.split(' ')[0].strip()

def generate_ticket(data: Dict[str, Any], agencia_obj=None):
    from core.services.parsers.pdf_generation import PdfGenerationService
    return PdfGenerationService.generate_ticket(data, agencia_obj)
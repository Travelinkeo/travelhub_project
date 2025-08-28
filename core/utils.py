# Utilidades compartidas (quick win DRY)
from typing import Any, Iterable
import re

# Tokens de ubicación usados para recortar contaminación en nombres de pasajero.
# Incluye tanto frases compuestas como tokens individuales; fusiona listas previas de ticket_parser/pdf_generator.
LOCATION_TOKENS = [
    # Países / ciudades comunes
    'VENEZUELA', 'CARACAS', 'COLOMBIA', 'BOGOTA', 'PANAMA', 'LIMA', 'PERU', 'MEXICO', 'MIAMI', 'FLORIDA',
    'MEDELLIN', 'QUITO', 'ECUADOR', 'CALI', 'BARRANQUILLA', 'CARTAGENA',
    # Componentes de frases compuestas
    'CIUDAD', 'DE', 'CIUDAD DE PANAMA', 'UNITED', 'STATES', 'UNITED STATES', 'SAN', 'JOSE', 'SANTO', 'DOMINGO',
    # Variantes abreviadas observadas
    'COLOM', 'USA'
]

STOP_NAME_TOKENS = [
    ' FOID', ' ADDRESS', ' ISSUE', ' NIT', ' TICKET', ' OFFICE ID', ' TELEPHONE', ' MAIL INFO',
    ' CODIGO DE RESERVA', ' BOOKING REF', ' FECHA DE EMISION', ' AGENTE EMISOR'
]

# Whitelist por defecto de nombres de pila comunes que NO deben eliminarse aunque aparezcan en LOCATION_TOKENS.
DEFAULT_FIRST_NAME_WHITELIST = {"JOSE", "MARIA", "ANA", "EMMA", "OSCAR", "ANGEL", "ÁNGEL"}

def get_first_name_whitelist() -> set[str]:
    """Obtiene la whitelist de nombres de pila.

    Permite override vía settings.PASSENGER_FIRST_NAME_WHITELIST si existe (iterable de strings).
    Si settings no está disponible (por ejemplo en scripts aislados) o no define la variable, retorna la constante por defecto.
    """
    try:
        from django.conf import settings  # type: ignore
        custom = getattr(settings, 'PASSENGER_FIRST_NAME_WHITELIST', None)
        if custom:
            if isinstance(custom, (set, list, tuple)):
                return {str(x).upper() for x in custom}
            # Permitir string separada por comas
            if isinstance(custom, str):
                return {s.strip().upper() for s in custom.split(',') if s.strip()}
    except Exception:
        pass
    return {n.upper() for n in DEFAULT_FIRST_NAME_WHITELIST}

def sanitize_passenger_name(nombre: str) -> str:
    """Limpia un nombre de pasajero que puede venir contaminado con ciudades / países.

    Reglas (replicadas desde pdf_generator._sanitize_nombre_pasajero):
    1. Remover bloques finales entre paréntesis que aparenten ser ubicaciones (p.ej. "(CIUDAD DE PANAMA) (PANAMA)").
    2. Colapsar espacios múltiples.
    3. Remover un único paréntesis corto residual final (<=5 chars) p.ej. "(VE)".
    4. Si el nombre tiene formato "APELLIDOS/NOMBRES", intentar recortar secuencia de tokens de ubicación al final de la parte de nombres
       usando LOCATION_TOKENS (ej: "PEREZ/JOSE CIUDAD DE PANAMA PANAMA" -> "PEREZ/JOSE").
       También recorta un único token final de ubicación ("FLORIDA").
    Mantiene otros caracteres válidos y no altera nombres que no cumplan criterios de contaminación.
    """
    if not nombre:
        return nombre
    candidate = nombre.strip()
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑ ")
    # 1) Remover múltiples bloques paréntesis finales que parezcan ubicaciones
    while candidate.endswith(')'):
        open_idx = candidate.rfind('(')
        if open_idx == -1:
            break
        inner = candidate[open_idx+1:-1].strip()
        upper_inner = inner.upper()
        if (len(inner) >= 2 and all(c in allowed_chars for c in upper_inner)
            and ((' ' in inner) or 'DE' in upper_inner or 'DEL' in upper_inner or (inner.isalpha() and len(inner) >= 4))):
            candidate = candidate[:open_idx].rstrip()
            continue
        break
    # 2) Normalizar espacios múltiples
    candidate = re.sub(r'\s{2,}', ' ', candidate).strip()
    # 3) Remover paréntesis corto residual al final
    candidate = re.sub(r'\s*\([A-ZÁÉÍÓÚÑ ]{1,5}\)$', '', candidate).strip()
    # 4) Recorte de tokens de ubicación al final de la parte de nombres
    LOCATION_TOKENS_SET = {t.upper() for t in LOCATION_TOKENS}
    if '/' in candidate:
        apellidos, nombres = candidate.split('/', 1)
        nombres = nombres.strip()
        # Remover frase tipo "CIUDAD DE XXXX ..." completa al final
        nombres = re.sub(r'(?:CIUDAD DE [A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*)$', '', nombres).strip()
        tokens = nombres.split()
        if len(tokens) > 1:
            for i in range(1, len(tokens)):
                tail = tokens[i:]
                if tail and all(t in LOCATION_TOKENS_SET for t in tail):
                    tokens = tokens[:i]
                    break
            else:
                # Caso simple un token final
                if tokens and tokens[-1] in LOCATION_TOKENS_SET:
                    tokens = tokens[:-1]
        elif tokens:
            # Solo un token: eliminarlo SOLO si es claramente ubicación y no un nombre común.
            whitelist = get_first_name_whitelist()
            token_up = tokens[0].upper()
            if token_up in LOCATION_TOKENS_SET and token_up not in whitelist:
                tokens = []
        nombres_limpios = ' '.join(tokens)
        candidate = f"{apellidos.strip()}/{nombres_limpios}".strip()
    return candidate

def clean_simple(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()

def strip_trailing_location_fragment(upper_text: str) -> str:
    # Elimina fragmentos de ubicación al final de un nombre
    for token in LOCATION_TOKENS:
        pattern = fr'(.*?)\b{re.escape(token)}\b.*$'
        m = re.match(pattern, upper_text)
        if m:
            return m.group(1).strip()
    return upper_text.strip()

def truncate_on_stop_tokens(upper_text: str) -> str:
    for token in STOP_NAME_TOKENS:
        idx = upper_text.find(token)
        if idx != -1:
            return upper_text[:idx].strip()
    return upper_text

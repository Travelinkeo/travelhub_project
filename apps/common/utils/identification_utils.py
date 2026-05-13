import re

FOID_LINE_REGEX = re.compile(r'^(?:FOID(?:/D\.IDENTIDAD)?|/?D\.IDENTIDAD)\s*:?-?\s*(.+)$', re.IGNORECASE)

def _limpiar_valor_foid(valor: str) -> str:
    """Aplica reglas de normalización sobre el fragmento derecho después del prefijo FOID/D.IDENTIDAD."""
    original = valor
    # Eliminar prefijos repetidos al inicio
    while True:
        nuevo = re.sub(r'^(?:/?D\.IDENTIDAD|FOID)\s*: ?\s*', '', valor, flags=re.IGNORECASE)
        if nuevo == valor:
            break
        valor = nuevo.strip()
    # Cortar antes de RIF
    rif = re.search(r'\bRIF\b', valor, flags=re.IGNORECASE)
    if rif:
        valor = valor[:rif.start()].strip()
    # Tomar primer token alfanumérico >=3 (pasaportes/IDs mínimos)
    m = re.search(r'\b([A-Z0-9]{3,})\b', valor.upper())
    if m:
        return m.group(1)
    m2 = re.search(r'([A-Z0-9]+)', valor.upper())
    if m2:
        return m2.group(1)
    return original.strip() or 'No encontrado'

def normalize_codigo_identificacion(linea_foid: str) -> str:
    """Recibe una *línea* que contiene FOID/D.IDENTIDAD y devuelve el código normalizado.

    Si no contiene el patrón esperado retorna 'No encontrado'.
    """
    if not linea_foid:
        return 'No encontrado'
    # Intentar casar regex de línea
    m = FOID_LINE_REGEX.search(linea_foid.strip())
    if not m:
        # Puede que venga sin saltos (inline con otros campos) -> buscar prefijo en medio
        inline = re.search(r'(?:FOID(?:/D\.IDENTIDAD)?|/?D\.IDENTIDAD)\s*:?-?\s*([^\n]+)', linea_foid, flags=re.IGNORECASE)
        if not inline:
            return 'No encontrado'
        return _limpiar_valor_foid(inline.group(1))
    return _limpiar_valor_foid(m.group(1))

def extract_codigo_identificacion_anywhere(texto: str) -> str:
    """Busca la primera ocurrencia de FOID/D.IDENTIDAD en cualquier parte del bloque de texto.

    Estrategia:
      1. Recorre línea por línea primero (preferencia a coincidencia limpia de línea).
      2. Si no encuentra, busca inline dentro del texto completo (caso pegado a otras etiquetas).
      3. Normaliza usando la misma función de limpieza.
    """
    if not texto:
        return 'No encontrado'
    # 1. Líneas
    for line in texto.splitlines():
        if 'FOID' in line.upper() or 'D.IDENTIDAD' in line.upper():
            m = FOID_LINE_REGEX.search(line.strip())
            if m:
                return _limpiar_valor_foid(m.group(1))
    # 2. Inline en todo el bloque
    inline = re.search(r'(?:FOID(?:/D\.IDENTIDAD)?|/?D\.IDENTIDAD)\s*:?-?\s*([A-Z0-9 /:-]{3,})', texto, flags=re.IGNORECASE)
    if inline:
        return _limpiar_valor_foid(inline.group(1))
    return 'No encontrado'

__all__ = ["normalize_codigo_identificacion", "extract_codigo_identificacion_anywhere"]

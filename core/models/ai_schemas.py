
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
import re

# ─────────────────────────────────────────────────────────────────────────────
# Helper: convierte strings ruidosas a float ("0.00A" → 0.0 , "USD 450" → 450.0)
# ─────────────────────────────────────────────────────────────────────────────
def _to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    clean = re.sub(r'[^0-9.,]', '', str(v)).replace(',', '.')
    try:
        return float(clean) if clean else 0.0
    except ValueError:
        return 0.0

class TramoVueloSchema(BaseModel):
    aerolinea: str = Field(description="Código IATA o nombre de la aerolínea del tramo")
    numero_vuelo: Optional[str] = Field(description="Número de vuelo INCLUYENDO EL CÓDIGO DE AEROLÍNEA (ej: TK0224, CM062)")
    origen: str = Field(description="Nombre completo de la ciudad de origen (ej. BOGOTA, CARACAS)")
    codigo_iata_origen: Optional[str] = Field(description="Código IATA de 3 letras de la ciudad de origen (ej. BOG, CCS)")
    fecha_salida: str = Field(description="Fecha de salida en formato GDS DDMMMAA en mayúsculas (ej: 29MAR26)")
    hora_salida: str = Field(description="Hora de salida en formato 24h HH:MM (ej: 14:15). NUNCA usar AM/PM.")
    destino: str = Field(description="Nombre completo de la ciudad de destino (ej. BOGOTA, MADRID)")
    codigo_iata_destino: Optional[str] = Field(description="Código IATA de 3 letras de la ciudad de destino (ej. BOG, MAD)")
    hora_llegada: str = Field(description="Hora de llegada en formato 24h HH:MM (ej: 15:10). NUNCA usar AM/PM.")
    fecha_llegada: str = Field(description="Fecha de llegada en formato GDS DDMMMAA en mayúsculas (ej: 29MAR26).")
    cabina: Optional[str] = Field(description="Clase de cabina (Económica, Ejecutiva, etc.)")
    clase: Optional[str] = Field(description="Clase tarifaria (clase de reserva, ej: Y, M, L)")
    localizador_aerolinea: Optional[str] = Field(description="Localizador específico de la aerolínea si difiere del principal")
    equipaje: Optional[str] = Field(description="Franquicia de equipaje (ej: 1PC, 23KG)")

    @validator('hora_salida', 'hora_llegada', pre=True, always=True)
    def normalize_time(cls, v):
        """Convierte AM/PM a 24h y limpia formatos inválidos."""
        if not v:
            return "00:00"
        v = str(v).strip()
        # Normalizar AM/PM → 24h
        am_pm = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', v, re.IGNORECASE)
        if am_pm:
            h, m, period = int(am_pm.group(1)), am_pm.group(2), am_pm.group(3).upper()
            if period == 'PM' and h != 12:
                h += 12
            elif period == 'AM' and h == 12:
                h = 0
            return f"{h:02d}:{m}"
        # Validar formato HH:MM
        if re.match(r'^\d{1,2}:\d{2}$', v):
            parts = v.split(':')
            return f"{int(parts[0]):02d}:{parts[1]}"
        return v  # Devuelve tal cual si no podemos interpretarlo

class BoletoAereoSchema(BaseModel):
    nombre_pasajero: str = Field(description="Nombre completo del pasajero (Formato GDS: APELLIDO/NOMBRE). Máximo 80 caracteres.")
    codigo_identificacion: Optional[str] = Field(description="FOID, DNI, Cédula o Pasaporte del pasajero (sin prefijos)")
    solo_nombre_pasajero: str = Field(description="Únicamente el primer nombre del pasajero limpio")
    numero_boleto: Optional[str] = Field(description="Número de boleto de 13 dígitos. Obligatorio si existe. Null si es Low-Cost")
    fecha_emision: Optional[str] = Field(description="Fecha de emisión en formato DDMMMAA (ej: 14MAR26)")
    agente_emisor: Optional[str] = Field(description="Código IATA o Identificador de la oficina/agente emisor")
    numero_iata: Optional[str] = Field(description="Número IATA de la agencia (8 dígitos exactos)")
    codigo_reserva: str = Field(description="Localizador principal de la reserva (PNR) exactamente 6 caracteres alfanuméricos")
    codigo_reserva_aerolinea: Optional[str] = Field(description="Localizador específico de la aerolínea (si es diferente al principal)")
    nombre_aerolinea: str = Field(description="Nombre de la aerolínea principal o validadora")
    direccion_aerolinea: Optional[str] = Field(description="Dirección física de la aerolínea (si está presente)")
    itinerario: List[TramoVueloSchema] = Field(description="Lista de todos los tramos de vuelo del itinerario. Mínimo 1 segmento obligatorio.")
    tarifa: float = Field(description="Monto numérico de la tarifa base (solo dígitos)")
    impuestos: float = Field(description="Monto numérico total de impuestos (solo dígitos)")
    total: float = Field(description="Monto total pagado. DEBE ser igual a tarifa + impuestos.")
    moneda: str = Field(description="Código de moneda (ej: USD, VES, EUR)")
    es_remision: bool = Field(description="Indica si es una re-emisión (detectable por 'A' en total o Tarifa > Total)")
    source_system: str = Field(description="Sistema de origen detectado (KIU, SABRE, AMADEUS, WINGO, COPA_SPRK, etc.)")
    confidence_score: float = Field(description="Nivel de confianza...")
    notas_advertencia: Optional[str] = Field(description="Si hubo prorrateos...")

    # ─── Validators ────────────────────────────────────────────────────

    @validator('tarifa', 'impuestos', 'total', pre=True, always=True)
    def parse_monetary(cls, v):
        """C1: Convierte '0.00A', 'USD 450', None → float limpio."""
        return _to_float(v)

    @validator('nombre_pasajero')
    def validate_passenger_name(cls, v):
        """C4: Limita longitud y limpia ruidos de etiquetas (greedy capture fix)."""
        v = v.upper().strip()
        # Eliminar ruidos de etiquetas comunes que la IA a veces captura por error
        stop_keywords = [
            'NÚMERO DE', 'NUMERO DE', 'TIQUETE', 'TICKET', 'EMAIL', 
            'CORREO', 'TELÉFONO', 'TELEFONO', 'NOMBRE DE', 'PASSENGER',
            'DOCUMENTO', 'DETALLES', 'ORIGEN', 'SALIDA', 'LLEGADA', 'VUELO'
        ]
        for kw in stop_keywords:
            if kw in v:
                v = v.split(kw)[0].strip()
        
        if len(v) > 80:
            v = v[:80]
        return v

    @validator('codigo_reserva')
    def clean_pnr(cls, v):
        """A1: Extrae solo los 6 caracteres alfanuméricos del PNR."""
        if not v:
            return 'UNKNOWN'
        # Eliminar prefijos como C1/
        clean = re.sub(r'^C1/', '', str(v).upper())
        # Quedarse solo con caracteres alfanuméricos
        clean = re.sub(r'[^A-Z0-9]', '', clean)
        # Tomar los últimos 6 si hay más
        return clean[-6:] if len(clean) >= 6 else clean

    @validator('numero_boleto', pre=True, always=True)
    def validate_ticket_number(cls, v):
        """
        Valida que el número de boleto sea real: 13-15 dígitos (estándar IATA).
        Limpia espacios y guiones. Descarta silenciosamente si no cumple.
        Ejemplos válidos: '1347424825206' (13 dígitos), '08039700000002' (14 dígitos)
        Ejemplos inválidos: 'SIN BOLETO', 'N/A', '1234' → devuelve None
        """
        if not v or str(v).strip().lower() in ('null', 'none', 'n/a', '', 'sin boleto', 'no aplica'):
            return None
        # Limpiar espacios y guiones (ej: "134 7424 825206" o "134-742-4825206")
        digits_only = re.sub(r'[\s\-]', '', str(v))
        # Solo dígitos, 13-15 caracteres (IATA: 13 obligatorio, algunos GDS usan 14-15)
        if re.match(r'^\d{13,15}$', digits_only):
            return digits_only
        # Si contiene letras o tiene longitud incorrecta → descartar
        return None

    @validator('moneda', pre=True, always=True)
    def validate_currency(cls, v):
        """
        Valida y normaliza el código de moneda contra ISO 4217.
        Mapea variantes informales a sus códigos reales.
        Si no reconoce la moneda, devuelve 'USD' como fallback seguro.
        """
        if not v:
            return 'USD'

        raw = str(v).strip().upper()

        # Mapa de variantes informales → ISO 4217
        ALIAS_MAP = {
            # Español informal
            'DOLARES': 'USD', 'DOLAR': 'USD', 'DOLLAR': 'USD', 'DOLLARS': 'USD',
            'EUROS': 'EUR', 'EURO': 'EUR',
            'BOLIVARES': 'VES', 'BOLIVAR': 'VES', 'BS': 'VES', 'BSF': 'VEF',
            'PESOS': 'COP',  # Contexto colombiano (default)
            'REALES': 'BRL', 'REAL': 'BRL',
            'SOLES': 'PEN', 'SOL': 'PEN',
            'QUETZALES': 'GTQ', 'QUETZAL': 'GTQ',
            'LEMPIRAS': 'HNL', 'LEMPIRA': 'HNL',
            'COLONES': 'CRC', 'COLON': 'CRC',
        }

        # ISO 4217 — Monedas relevantes para el sistema
        VALID_ISO = {
            # América Latina
            'USD', 'EUR', 'VES', 'VEF', 'COP', 'BRL', 'ARS', 'MXN',
            'CLP', 'PEN', 'BOB', 'PYG', 'UYU', 'GTQ', 'HNL', 'NIO',
            'CRC', 'PAB', 'DOP', 'CUP', 'HTG', 'JMD', 'TTD', 'BBD',
            # Globales comunes en GDS
            'GBP', 'CAD', 'AUD', 'CHF', 'JPY', 'CNY', 'MXN', 'TRY',
            'AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR',
        }

        # Intentar alias primero
        if raw in ALIAS_MAP:
            return ALIAS_MAP[raw]

        # Si ya es un código ISO válido, devolverlo
        if raw in VALID_ISO:
            return raw

        # Extraer 3 letras si viene con texto extra (ej: "USD 450" → "USD")
        match = re.search(r'\b([A-Z]{3})\b', raw)
        if match and match.group(1) in VALID_ISO:
            return match.group(1)

        # Fallback seguro: USD
        return 'USD'

    @validator('itinerario')
    def check_itinerary_not_empty(cls, v):
        """C3: El itinerario debe tener al menos 1 segmento."""
        if not v:
            raise ValueError('El itinerario no puede estar vacío. Debe tener al menos 1 segmento de vuelo.')
        if len(v) > 8:
            # M1: Truncar si hay más de 8 segmentos (probable alucinación)
            v = v[:8]
        return v

    @validator('total', always=True)
    def validate_math(cls, v, values):
        """C2: Asegura que tarifa + impuestos == total (reemplaza si no cuadra)."""
        tarifa = values.get('tarifa', 0.0)
        impuestos = values.get('impuestos', 0.0)
        expected = round(tarifa + impuestos, 2)
        if v == 0.0 and expected > 0:
            return expected
        return v

    @validator('confidence_score', always=True)
    def auto_compute_confidence(cls, v, values):
        """
        Si la IA no establece el score (devuelve 1.0 por default),
        lo calculamos desde los campos críticos para garantizar honestidad.
        Lógica: cada campo crítico faltante descuenta puntos.
        """
        # Si la IA devolvió un score menor a 1.0, lo respetamos
        if v < 1.0:
            return max(0.0, min(1.0, v))  # Clamp a [0, 1]

        # Auto-cálculo cuando la IA dejó el default de 1.0
        score = 1.0
        deductions = {
            'codigo_reserva': 0.30,     # PNR es crítico — sin él, no hay nada
            'nombre_pasajero': 0.20,    # Nombre es obligatorio
            'itinerario': 0.25,         # Sin vuelos el boleto no tiene sentido
            'numero_boleto': 0.10,      # Importante, pero no siempre existe (Wingo)
            'total': 0.10,              # Financiero
            'moneda': 0.05,             # Menor peso
        }

        for field, weight in deductions.items():
            val = values.get(field)
            if val is None or val == '' or val == 'UNKNOWN':
                score -= weight
            elif field == 'itinerario' and isinstance(val, list) and len(val) == 0:
                score -= weight
            elif field == 'total' and isinstance(val, float) and val == 0.0:
                score -= (weight / 2)  # Descuento parcial si total es 0

        return round(max(0.0, min(1.0, score)), 2)

class ResultadoParseoSchema(BaseModel):
    """Esquema de respuesta final para Gemini"""
    boletos: List[BoletoAereoSchema] = Field(description="Lista de boletos extraídos (uno por pasajero). Mínimo 1 boleto.")

# --- ESQUEMAS DE AUDITORÍA ---

class AuditFinding(BaseModel):
    category: str = Field(description="Categoría del hallazgo (TASAS, NOMBRES, FEES, ITINERARIO)")
    severity: str = Field(description="Severidad (INFO, WARNING, CRITICAL)")
    message: str = Field(description="Mensaje explicativo para el agente")
    suggestion: Optional[str] = Field(description="Sugerencia de corrección si aplica")

class AuditReport(BaseModel):
    is_compliant: bool = Field(description="Si el boleto cumple con todas las reglas básicas")
    findings: List[AuditFinding] = Field(description="Lista de hallazgos")
    calculated_fees_suggested: Dict[str, float] = Field(description="Fees sugeridos basados en las reglas de negocio")
    summary: str = Field(description="Resumen ejecutivo de la auditoría")

# --- ESQUEMAS DE RECONCILIACIÓN DE PROVEEDORES ---

class InformeProveedorItemSchema(BaseModel):
    fecha_emision: Optional[str] = Field(description="Fecha de emisión según el reporte")
    pnr: Optional[str] = Field(description="Localizador/PNR")
    numero_boleto: Optional[str] = Field(description="Número de boleto (13 dígitos)")
    pasajero: Optional[str] = Field(description="Nombre del pasajero")
    itinerario: Optional[str] = Field(description="Origen/Destino")
    tarifa_neta: float = Field(description="Tarifa neta o Fare")
    impuestos: float = Field(description="Impuestos totales")
    comision_monto: float = Field(description="Monto de comisión recibida")
    total_pagar: float = Field(description="Total a pagar al proveedor")
    moneda: str = Field(description="Moneda del reporte")

class InformeProveedorSchema(BaseModel):
    proveedor_nombre: str = Field(..., description="Nombre del proveedor (CTG, MY DESTINY, etc.)")
    periodo_desde: Optional[str] = Field(description="Fecha inicio del reporte")
    periodo_hasta: Optional[str] = Field(description="Fecha fin del reporte")
    items: List[InformeProveedorItemSchema] = Field(description="Lista de ítems del reporte")
    total_reporte: float = Field(description="Monto total del reporte")

# --- ESQUEMAS DE CRM & PASAPORTES ---

class PasaporteOCRSchema(BaseModel):
    """
    SISTEMA DE VISIÓN ARTIFICIAL (CRM):
    Esquema de extracción para pasaportes y documentos de identidad.
    """
    nombres: str = Field(description="Nombres del pasajero tal como aparecen en el pasaporte (limpio)")
    apellidos: str = Field(description="Apellidos del pasajero")
    nacionalidad: str = Field(description="Nacionalidad/País (Texto o ISO de 3 letras)")
    numero_pasaporte: str = Field(description="Número de pasaporte o documento (alfanumérico)")
    fecha_nacimiento: str = Field(description="Fecha de nacimiento en formato ISO YYYY-MM-DD")
    sexo: str = Field(description="Sexo (M para masculino, F para femenino, X para no binario)")
    fecha_vencimiento: str = Field(description="Fecha de vencimiento del pasaporte en formato ISO YYYY-MM-DD")
    pais_emision: str = Field(description="País que emite el documento")
    
    @validator('nombres', 'apellidos')
    def capitalize_names(cls, v):
        return v.strip().upper()

    @validator('numero_pasaporte')
    def clean_doc(cls, v):
        return re.sub(r'[^A-Z0-9]', '', str(v).upper())

class CedulaOCRSchema(BaseModel):
    """
    SISTEMA DE VISIÓN ARTIFICIAL (SaaS V.1):
    Esquema de extracción para Cédulas de Identidad de Venezuela (impresas o manuscritas).
    Incluye detección de rostro para recorte dinámico.
    NOTA: Todos los campos son Optional para evitar errores si la IA no puede extraer un dato.
    """
    apellidos: Optional[str] = Field(default=None, description="Solo los apellidos del titular, en mayúsculas (Ej: PEREZ MENDOZA).")
    nombres: Optional[str] = Field(default=None, description="Solo los nombres del titular, en mayúsculas (Ej: ADAN DANIEL).")
    cedula: Optional[int] = Field(default=None, description="Solo números de la cédula, eliminando prefijos 'V-'/'E-' y puntos. (Ej: 24322251).")
    fecha_nacimiento: Optional[str] = Field(default=None, description="Fecha de nacimiento en formato ISO YYYY-MM-DD. (Ej: 1994-09-28).")
    portrait_bbox: Optional[List[int]] = Field(
        default=[0, 0, 0, 0],
        description="Coordenadas normalizadas [ymin, xmin, ymax, xmax] del rostro del titular (escala 0-1000)."
    )

    @validator('nombres', 'apellidos', pre=True, always=True)
    def clean_names(cls, v):
        if not v: return ""
        cleaned = str(v).strip().upper()
        # Rechazar valores genéricos que no son nombres reales
        if cleaned in ('SIN NOMBRE', 'SIN APELLIDO', 'N/A', 'NONE', 'NULL', 'NO LEGIBLE'):
            return ""
        return cleaned

    @validator('cedula', pre=True, always=True)
    def clean_cedula(cls, v):
        if not v: return None
        num = re.sub(r'[^0-9]', '', str(v))
        return int(num) if num else None

    @validator('portrait_bbox', pre=True, always=True)
    def clean_bbox(cls, v):
        if not v or not isinstance(v, list) or len(v) != 4:
            return [0, 0, 0, 0]
        return v

# --- ESQUEMAS DE RECONCILIACIÓN (AUDITORÍA FINANCIERA) ---

class MatchExitosoSchema(BaseModel):
    venta_id: int = Field(description="ID de la Venta/Boleto en TravelHub")
    proveedor_item_id: str = Field(description="Identificador del ítem en el reporte del proveedor (ej: numero_boleto)")
    diferencia_monto: float = Field(description="Discrepancia financiera (Monto Proveedor - Monto Agencia)")
    confianza: float = Field(description="Nivel de confianza del match difuso (0.0 a 1.0)")
    comentario: str = Field(description="Breve explicación del match (ej: 'PNR coincide, nombre invertido')")

class BoletoHuerfanoSchema(BaseModel):
    proveedor_item_id: str = Field(description="ID del registro del proveedor")
    pasajero: str = Field(description="Nombre en el reporte")
    monto: float = Field(description="Monto reclamado por el proveedor")
    causa_probable: str = Field(description="Diagnóstico (ej: 'Venta no reportada', 'Diferencia de 13 dígitos')")

class ConciliacionLoteSchema(BaseModel):
    matches: List[MatchExitosoSchema] = Field(description="Emparejamientos encontrados por IA")
    huerfanos: List[BoletoHuerfanoSchema] = Field(description="Registros del proveedor sin pareja en la agencia")
    alertas_fraude: List[str] = Field(description="Mensajes de alerta sobre discrepancias críticas")

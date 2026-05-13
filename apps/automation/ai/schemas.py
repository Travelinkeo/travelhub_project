import re

from pydantic import BaseModel, Field, validator


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, int | float):
        return float(v)
    clean = re.sub(r'[^0-9.,]', '', str(v)).replace(',', '.')
    try:
        return float(clean) if clean else 0.0
    except ValueError:
        return 0.0

# ─────────────────────────────────────────────────────────────────────────────
# GDS & TICKET PARSING SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class TramoVueloSchema(BaseModel):
    aerolinea: str = Field(description="Código IATA o nombre de la aerolínea del tramo")
    numero_vuelo: str | None = Field(description="Número de vuelo INCLUYENDO EL CÓDIGO DE AEROLÍNEA (ej: TK0224, CM062)")
    origen: str = Field(description="Nombre completo de la ciudad de origen (ej. BOGOTA, CARACAS)")
    codigo_iata_origen: str | None = Field(description="Código IATA de 3 letras de la ciudad de origen (ej. BOG, CCS)")
    fecha_salida: str = Field(description="Fecha de salida en formato GDS DDMMMAA en mayúsculas (ej: 29MAR26)")
    hora_salida: str = Field(description="Hora de salida en formato 24h HH:MM (ej: 14:15). NUNCA usar AM/PM.")
    destino: str = Field(description="Nombre completo de la ciudad de destino (ej. BOGOTA, MADRID)")
    codigo_iata_destino: str | None = Field(description="Código IATA de 3 letras de la ciudad de destino (ej. BOG, MAD)")
    hora_llegada: str = Field(description="Hora de llegada en formato 24h HH:MM (ej: 15:10). NUNCA usar AM/PM.")
    fecha_llegada: str = Field(description="Fecha de llegada en formato GDS DDMMMAA en mayúsculas (ej: 29MAR26).")
    cabina: str | None = Field(description="Clase de cabina (Económica, Ejecutiva, etc.)")
    clase: str | None = Field(description="Clase tarifaria (clase de reserva, ej: Y, M, L)")
    localizador_aerolinea: str | None = Field(description="Localizador específico de la aerolínea si difiere del principal")
    equipaje: str | None = Field(description="Franquicia de equipaje (ej: 1PC, 23KG)")

    @validator('hora_salida', 'hora_llegada', pre=True, always=True)
    def normalize_time(cls, v):
        if not v:
            return "00:00"
        v = str(v).strip()
        am_pm = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', v, re.IGNORECASE)
        if am_pm:
            h, m, period = int(am_pm.group(1)), am_pm.group(2), am_pm.group(3).upper()
            if period == 'PM' and h != 12:
                h += 12
            elif period == 'AM' and h == 12:
                h = 0
            return f"{h:02d}:{m}"
        if re.match(r'^\d{1,2}:\d{2}$', v):
            parts = v.split(':')
            return f"{int(parts[0]):02d}:{parts[1]}"
        return v

class BoletoAereoSchema(BaseModel):
    nombre_pasajero: str = Field(description="Nombre completo del pasajero (Formato GDS: APELLIDO/NOMBRE). Máximo 80 caracteres.")
    codigo_identificacion: str | None = Field(description="FOID, DNI, Cédula o Pasaporte del pasajero (sin prefijos)")
    solo_nombre_pasajero: str = Field(description="Únicamente el primer nombre del pasajero limpio")
    numero_boleto: str | None = Field(description="Número de boleto de 13 dígitos. Obligatorio si existe. Null si es Low-Cost")
    fecha_emision: str | None = Field(description="Fecha de emisión en formato DDMMMAA (ej: 14MAR26)")
    agente_emisor: str | None = Field(description="Código IATA o Identificador de la oficina/agente emisor")
    numero_iata: str | None = Field(description="Número IATA de la agencia (8 dígitos exactos)")
    codigo_reserva: str = Field(description="Localizador principal de la reserva (PNR) exactamente 6 caracteres alfanuméricos")
    codigo_reserva_aerolinea: str | None = Field(description="Localizador específico de la aerolínea (si es diferente al principal)")
    nombre_aerolinea: str = Field(description="Nombre de la aerolínea principal o validadora")
    direccion_aerolinea: str | None = Field(description="Dirección física de la aerolínea (si está presente)")
    itinerario: list[TramoVueloSchema] = Field(description="Lista de todos los tramos de vuelo del itinerario. Mínimo 1 segmento obligatorio.")
    tarifa: float = Field(description="Monto numérico de la tarifa base (solo dígitos)")
    impuestos: float = Field(description="Monto numérico total de impuestos (solo dígitos)")
    total: float = Field(description="Monto total pagado. DEBE ser igual a tarifa + impuestos.")
    moneda: str = Field(description="Código de moneda (ej: USD, VES, EUR)")
    es_remision: bool = Field(description="Indica si es una re-emisión (detectable por 'A' en total o Tarifa > Total)")
    source_system: str = Field(description="Sistema de origen detectado (KIU, SABRE, AMADEUS, WINGO, COPA_SPRK, etc.)")
    confidence_score: float = Field(description="Nivel de confianza...")
    notas_advertencia: str | None = Field(description="Si hubo prorrateos...")

    @validator('tarifa', 'impuestos', 'total', pre=True, always=True)
    def parse_monetary(cls, v):
        return _to_float(v)

    @validator('nombre_pasajero')
    def validate_passenger_name(cls, v):
        v = v.upper().strip()
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
        if not v:
            return 'UNKNOWN'
        clean = re.sub(r'^C1/', '', str(v).upper())
        clean = re.sub(r'[^A-Z0-9]', '', clean)
        return clean[-6:] if len(clean) >= 6 else clean

    @validator('numero_boleto', pre=True, always=True)
    def validate_ticket_number(cls, v):
        if not v or str(v).strip().lower() in ('null', 'none', 'n/a', '', 'sin boleto', 'no aplica'):
            return None
        digits_only = re.sub(r'[\s\-]', '', str(v))
        if re.match(r'^\d{13,15}$', digits_only):
            return digits_only
        return None

    @validator('moneda', pre=True, always=True)
    def validate_currency(cls, v):
        if not v: return 'USD'
        raw = str(v).strip().upper()
        ALIAS_MAP = {
            'DOLARES': 'USD', 'DOLAR': 'USD', 'DOLLAR': 'USD', 'DOLLARS': 'USD',
            'EUROS': 'EUR', 'EURO': 'EUR',
            'BOLIVARES': 'VES', 'BOLIVAR': 'VES', 'BS': 'VES', 'BSF': 'VEF',
            'PESOS': 'COP', 'REALES': 'BRL', 'REAL': 'BRL',
            'SOLES': 'PEN', 'SOL': 'PEN', 'QUETZALES': 'GTQ', 'QUETZAL': 'GTQ',
            'LEMPIRAS': 'HNL', 'LEMPIRA': 'HNL', 'COLONES': 'CRC', 'COLON': 'CRC',
        }
        VALID_ISO = {
            'USD', 'EUR', 'VES', 'VEF', 'COP', 'BRL', 'ARS', 'MXN',
            'CLP', 'PEN', 'BOB', 'PYG', 'UYU', 'GTQ', 'HNL', 'NIO',
            'CRC', 'PAB', 'DOP', 'CUP', 'HTG', 'JMD', 'TTD', 'BBD',
            'GBP', 'CAD', 'AUD', 'CHF', 'JPY', 'CNY', 'TRY',
            'AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR',
        }
        if raw in ALIAS_MAP: return ALIAS_MAP[raw]
        if raw in VALID_ISO: return raw
        match = re.search(r'\b([A-Z]{3})\b', raw)
        if match and match.group(1) in VALID_ISO: return match.group(1)
        return 'USD'

    @validator('itinerario')
    def check_itinerary_not_empty(cls, v):
        if not v: raise ValueError('El itinerario no puede estar vacío.')
        return v[:8]

    @validator('total', always=True)
    def validate_math(cls, v, values):
        tarifa = values.get('tarifa', 0.0)
        impuestos = values.get('impuestos', 0.0)
        expected = round(tarifa + impuestos, 2)
        if v == 0.0 and expected > 0: return expected
        return v

    @validator('confidence_score', always=True)
    def auto_compute_confidence(cls, v, values):
        if v < 1.0: return max(0.0, min(1.0, v))
        score = 1.0
        deductions = {'codigo_reserva': 0.30, 'nombre_pasajero': 0.20, 'itinerario': 0.25, 'numero_boleto': 0.10, 'total': 0.10, 'moneda': 0.05}
        for field, weight in deductions.items():
            val = values.get(field)
            if val is None or val == '' or val == 'UNKNOWN': score -= weight
            elif field == 'itinerario' and isinstance(val, list) and len(val) == 0: score -= weight
            elif field == 'total' and isinstance(val, float) and val == 0.0: score -= (weight / 2)
        return round(max(0.0, min(1.0, score)), 2)

class ResultadoParseoSchema(BaseModel):
    boletos: list[BoletoAereoSchema] = Field(description="Lista de boletos extraídos (uno por pasajero). Mínimo 1 boleto.")

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT & COMPLIANCE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class AuditFinding(BaseModel):
    category: str = Field(description="Categoría del hallazgo (TASAS, NOMBRES, FEES, ITINERARIO)")
    severity: str = Field(description="Severidad (INFO, WARNING, CRITICAL)")
    message: str = Field(description="Mensaje explicativo para el agente")
    suggestion: str | None = Field(description="Sugerencia de corrección si aplica")

class AuditReport(BaseModel):
    is_compliant: bool = Field(description="Si el boleto cumple con todas las reglas básicas")
    findings: list[AuditFinding] = Field(description="Lista de hallazgos")
    calculated_fees_suggested: dict[str, float] = Field(description="Fees sugeridos basados en las reglas de negocio")
    summary: str = Field(description="Resumen ejecutivo de la auditoría")

# ─────────────────────────────────────────────────────────────────────────────
# SUPPLIER RECONCILIATION SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class InformeProveedorItemSchema(BaseModel):
    fecha_emision: str | None = Field(description="Fecha de emisión según el reporte")
    pnr: str | None = Field(description="Localizador/PNR")
    numero_boleto: str | None = Field(description="Número de boleto (13 dígitos)")
    pasajero: str | None = Field(description="Nombre del pasajero")
    itinerario: str | None = Field(description="Origen/Destino")
    tarifa_neta: float = Field(description="Tarifa neta o Fare")
    impuestos: float = Field(description="Impuestos totales")
    comision_monto: float = Field(description="Monto de comisión recibida")
    total_pagar: float = Field(description="Total a pagar al proveedor")
    moneda: str = Field(description="Moneda del reporte")

class InformeProveedorSchema(BaseModel):
    proveedor_nombre: str = Field(..., description="Nombre del proveedor (CTG, MY DESTINY, etc.)")
    periodo_desde: str | None = Field(description="Fecha inicio del reporte")
    periodo_hasta: str | None = Field(description="Fecha fin del reporte")
    items: list[InformeProveedorItemSchema] = Field(description="Lista de ítems del reporte")
    total_reporte: float = Field(description="Monto total del reporte")

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
    matches: list[MatchExitosoSchema] = Field(description="Emparejamientos encontrados por IA")
    huerfanos: list[BoletoHuerfanoSchema] = Field(description="Registros del proveedor sin pareja en la agencia")
    alertas_fraude: list[str] = Field(description="Mensajes de alerta sobre discrepancias críticas")

# ─────────────────────────────────────────────────────────────────────────────
# VISION & OCR SCHEMAS (CRM)
# ─────────────────────────────────────────────────────────────────────────────

class PasaporteOCRSchema(BaseModel):
    nombres: str = Field(description="Nombres del pasajero tal como aparecen en el pasaporte (limpio)")
    apellidos: str = Field(description="Apellidos del pasajero")
    nacionalidad: str = Field(description="Nacionalidad/País (Texto o ISO de 3 letras)")
    numero_pasaporte: str = Field(description="Número de pasaporte o documento (alfanumérico)")
    fecha_nacimiento: str = Field(description="Fecha de nacimiento en formato ISO YYYY-MM-DD")
    sexo: str = Field(description="Sexo (M para masculino, F para femenino, X para no binario)")
    fecha_vencimiento: str = Field(description="Fecha de vencimiento del pasaporte en formato ISO YYYY-MM-DD")
    pais_emision: str = Field(description="País que emite el documento")
    
    @validator('nombres', 'apellidos')
    def capitalize_names(cls, v): return v.strip().upper()

    @validator('numero_pasaporte')
    def clean_doc(cls, v): return re.sub(r'[^A-Z0-9]', '', str(v).upper())

class CedulaOCRSchema(BaseModel):
    apellidos: str | None = Field(default=None, description="Solo los apellidos del titular, en mayúsculas.")
    nombres: str | None = Field(default=None, description="Solo los nombres del titular, en mayúsculas.")
    cedula: int | None = Field(default=None, description="Solo números de la cédula.")
    fecha_nacimiento: str | None = Field(default=None, description="Fecha de nacimiento en formato ISO YYYY-MM-DD.")
    portrait_bbox: list[int] | None = Field(default=[0, 0, 0, 0], description="Coordenadas normalizadas [ymin, xmin, ymax, xmax] del rostro.")

    @validator('nombres', 'apellidos', pre=True, always=True)
    def clean_names(cls, v):
        if not v: return ""
        cleaned = str(v).strip().upper()
        if cleaned in ('SIN NOMBRE', 'SIN APELLIDO', 'N/A', 'NONE', 'NULL', 'NO LEGIBLE'): return ""
        return cleaned

    @validator('cedula', pre=True, always=True)
    def clean_cedula(cls, v):
        if not v: return None
        num = re.sub(r'[^0-9]', '', str(v))
        return int(num) if num else None

# ─────────────────────────────────────────────────────────────────────────────
# BI & BUSINESS ADVISOR SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ConsejosIASchema(BaseModel):
    saludo: str = Field(description="Un saludo enérgico para el CEO (ej. '¡Buen día, equipo directivo!')")
    diagnostico: str = Field(description="Un diagnóstico de 1 línea basado en las métricas")
    consejo_estrategico: str = Field(description="Un consejo de negocio basado en si las ventas suben o bajan")
    accion_recomendada: str = Field(description="Una recomendación directa (ej. 'Inicia trámites de Tax Refund para flujo de caja extra')")

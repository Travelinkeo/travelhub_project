from pydantic import BaseModel, Field, validator
from typing import List, Optional

class LineaAsientoSchema(BaseModel):
    """Representa una línea individual de un asiento contable."""
    codigo_cuenta: str = Field(description="Código exacto de la cuenta contable en el Plan de Cuentas (ej: 1.1.01.01)")
    nombre_cuenta: str = Field(description="Nombre legible de la cuenta para validación visual")
    debe: float = Field(default=0.0, description="Monto a cargar en el DEBE")
    haber: float = Field(default=0.0, description="Monto a abonar en el HABER")
    concepto: str = Field(description="Explicación específica de este movimiento de línea")

class AsientoContableSchema(BaseModel):
    """Esquema completo para la generación de asientos contables vía IA."""
    descripcion_general: str = Field(description="Resumen ejecutivo de la transacción")
    fecha_contable: str = Field(description="Fecha de registro en formato ISO YYYY-MM-DD")
    moneda: str = Field(default="USD", description="Código ISO de la moneda de la transacción")
    lineas: List[LineaAsientoSchema] = Field(description="Conjunto de movimientos contables")

    @validator('lineas')
    def validar_partida_doble(cls, v):
        """
        REGLA DE ORO DE LA CONTABILIDAD:
        Garantiza matemáticamente que el asiento esté cuadrado (Debe == Haber).
        Se permite una tolerancia de 0.01 para errores de redondeo.
        """
        total_debe = round(sum(l.debe for l in v), 2)
        total_haber = round(sum(l.haber for l in v), 2)
        
        if abs(total_debe - total_haber) > 0.01:
            raise ValueError(
                f"Violación de Partida Doble: El asiento está descuadrado. "
                f"Total Debe: {total_debe}, Total Haber: {total_haber}. "
                f"Diferencia: {abs(total_debe - total_haber)}"
            )
        return v

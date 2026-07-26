import datetime

from pydantic import BaseModel, Field, field_validator


class LineaAsientoSchema(BaseModel):
    codigo_cuenta: str = Field(..., min_length=1, description="Código de la cuenta contable (ej: 110101)")
    nombre_cuenta: str = Field(..., min_length=1, description="Nombre de la cuenta contable (ej: Caja General)")
    tipo: str = Field(..., pattern=r"^(DEBITO|CREDITO)$", description="DEBITO o CREDITO")
    monto_ves: float = Field(default=0.0, ge=0, description="Monto en bolívares (VES)")
    monto_usd: float = Field(default=0.0, ge=0, description="Monto en dólares (USD)")
    concepto: str = Field(default="", description="Descripción del movimiento")

    @field_validator("monto_ves", "monto_usd")
    @classmethod
    def validar_al_menos_un_monto(cls, v, info):
        return round(v, 2)


class AsientoContableSchema(BaseModel):
    glosa: str = Field(..., min_length=1, description="Descripción general del asiento contable")
    fecha_contable: str = Field(
        default_factory=lambda: datetime.date.today().isoformat(),
        description="Fecha contable en formato YYYY-MM-DD",
    )
    tipo_asiento: str = Field(
        default="DIARIO",
        pattern=r"^(DIARIO|VENTAS|AJUSTE|CIERRE)$",
        description="Tipo de asiento: DIARIO, VENTAS, AJUSTE o CIERRE",
    )
    lineas: list[LineaAsientoSchema] = Field(..., min_length=2, description="Líneas del asiento (mínimo 2 para partida doble)")

    @field_validator("fecha_contable")
    @classmethod
    def validar_fecha(cls, v):
        datetime.date.fromisoformat(v)
        return v

    @field_validator("lineas")
    @classmethod
    def validar_partida_doble(cls, lineas):
        total_debe_ves = sum(l.monto_ves for l in lineas if l.tipo == "DEBITO")
        total_haber_ves = sum(l.monto_ves for l in lineas if l.tipo == "CREDITO")
        total_debe_usd = sum(l.monto_usd for l in lineas if l.tipo == "DEBITO")
        total_haber_usd = sum(l.monto_usd for l in lineas if l.tipo == "CREDITO")

        if abs(total_debe_ves - total_haber_ves) > 0.01:
            raise ValueError(f"Partida doble VES no cuadra: debe {total_debe_ves} vs haber {total_haber_ves}")
        if abs(total_debe_usd - total_haber_usd) > 0.01:
            raise ValueError(f"Partida doble USD no cuadra: debe {total_debe_usd} vs haber {total_haber_usd}")

        return lineas

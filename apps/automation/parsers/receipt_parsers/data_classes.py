"""
Data classes for receipt parsers.
"""

from typing import Any


class MultiParsedTicketData:
    """
    Container for parsed ticket data from web receipts.
    Supports conversion to dict and Pydantic schemas.
    """

    def __init__(self, data: dict):
        self.data = data

    def to_dict(self) -> dict:
        return self.data

    def to_pydantic(self) -> Any:
        from core.api import (
            BoletoAereoSchema,
            ResultadoParseoSchema,
            TramoVueloSchema,
        )

        boletos_pydantic = []
        for t in self.data.get("tickets", []):
            itinerario = []
            for f in t.get("vuelos", []):
                itinerario.append(
                    TramoVueloSchema(
                        aerolinea=f.get("aerolinea")
                        or t.get("NOMBRE_AEROLINEA")
                        or "AVIOR AIRLINES",
                        numero_vuelo=f.get("numero_vuelo"),
                        origen=f.get("origen"),
                        codigo_iata_origen=f.get("codigo_iata_origen"),
                        fecha_salida=f.get("fecha_salida") or f.get("fecha") or "01JAN26",
                        hora_salida=f.get("hora_salida") or "00:00",
                        destino=f.get("destino"),
                        codigo_iata_destino=f.get("codigo_iata_destino"),
                        hora_llegada=f.get("hora_llegada") or "00:00",
                        fecha_llegada=f.get("fecha_llegada")
                        or f.get("fecha_salida")
                        or f.get("fecha")
                        or "01JAN26",
                        cabina=f.get("clase") or "Económica",
                        clase=f.get("clase"),
                        localizador_aerolinea=t.get("CODIGO_RESERVA"),
                    )
                )
            boletos_pydantic.append(
                BoletoAereoSchema(
                    nombre_pasajero=t.get("NOMBRE_DEL_PASAJERO") or "PASAJERO DESCONOCIDO",
                    solo_nombre_pasajero=t.get("SOLO_NOMBRE_PASAJERO") or "PASAJERO",
                    codigo_identificacion=t.get("CODIGO_IDENTIFICACION"),
                    numero_boleto=t.get("NUMERO_DE_BOLETO"),
                    fecha_emision=t.get("FECHA_EMISION"),
                    agente_emisor=t.get("AGENTE_EMISOR"),
                    codigo_reserva=t.get("CODIGO_RESERVA") or "UNKNOWN",
                    codigo_reserva_aerolinea=t.get("SOLO_CODIGO_RESERVA")
                    or t.get("CODIGO_RESERVA_AEROLINEA"),
                    nombre_aerolinea=t.get("NOMBRE_AEROLINEA") or "AVIOR AIRLINES",
                    direccion_aerolinea=t.get("DIRECCION_AEROLINEA"),
                    tarifa=float(t.get("TARIFA_IMPORTE") or 0.0),
                    impuestos=float(t.get("IMPUESTOS") or 0.0),
                    total=float(t.get("TOTAL_IMPORTE") or 0.0),
                    moneda=t.get("TOTAL_MONEDA") or "VES",
                    itinerario=itinerario,
                    source_system=t.get("SOURCE_SYSTEM") or "AVIOR_WEB",
                )
            )
        return ResultadoParseoSchema(boletos=boletos_pydantic)

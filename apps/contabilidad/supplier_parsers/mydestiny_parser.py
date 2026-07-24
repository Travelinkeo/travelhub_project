import io
import logging
import re
from decimal import Decimal
from typing import Any

import pypdf

from .base_parser import BaseSupplierReportParser

logger = logging.getLogger(__name__)


def parse_latin_decimal(val_str: str) -> Decimal:
    if not val_str or val_str.strip() in ["-", ""]:
        return Decimal("0.00")
    clean = val_str.replace("%", "").strip()
    clean = clean.replace(".", "").replace(",", ".")
    try:
        return Decimal(clean)
    except Exception:
        return Decimal("0.00")


def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    parts = date_str.strip().split("/")
    if len(parts) == 3:
        try:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if month > 12:
                day, month = month, day
            return f"{year:04d}-{month:02d}-{day:02d}"
        except Exception:
            pass
    return None


class MyDestinyReportParser(BaseSupplierReportParser):
    def parse(self) -> dict[str, Any]:
        reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes))
        full_text = "\n".join([page.extract_text() or "" for page in reader.pages])

        result: dict[str, Any] = {
            "proveedor_nombre": "MY DESTINY",
            "codigo_agencia_proveedor": "PTYS3650",
            "fecha_reporte_desde": None,
            "fecha_reporte_hasta": None,
            "saldo_anterior": Decimal("0.00"),
            "monto_total_ventas": Decimal("0.00"),
            "saldo_final": Decimal("0.00"),
            "items": [],
            "raw_text": full_text,
        }

        rep_ant = re.search(r"REPORTE ANTERIOR\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if rep_ant:
            result["saldo_anterior"] = parse_latin_decimal(rep_ant.group(1))

        dif_agv = re.search(
            r"Diferencia a favor\s+de\s+AGV\s+([\d\.\,-]+)", full_text, re.IGNORECASE
        )
        if dif_agv:
            result["saldo_final"] = parse_latin_decimal(dif_agv.group(1))

        totales_match = re.search(r"TOTALES.*?\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if totales_match:
            result["monto_total_ventas"] = parse_latin_decimal(totales_match.group(1))

        row_pattern = re.compile(
            r"^(\d{1,2}/\d{1,2}/\d{4})\s+([A-Z0-9]+)\s+([A-Z0-9]+)\s+([A-Z0-9\s\/]+?)\s+(\d{8,15})\s+([A-Z0-9\s]+?)\s+([\d\.\,-]+)\s+([\d\.\,-]+)\s+([\d\.\,-]+|-)\s+([\d\.\,-]+|-)\s+([\d\.\,-]+)\s+([\d\.\,-]+)\s+([\d\.\,-]+%?)\s+([\d\.\,-]+)\s+([\d\.\,-]+)$"
        )

        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        for line in lines:
            m = row_pattern.match(line)
            if m:
                fecha_em = parse_date(m.group(1))
                cod_ag = m.group(2).strip()
                pax = m.group(4).strip()
                tkt_no = m.group(5).strip()
                airline = m.group(6).strip()

                fare = parse_latin_decimal(m.group(7))
                tax = parse_latin_decimal(m.group(8))
                subtotal = parse_latin_decimal(m.group(11))
                fee = parse_latin_decimal(m.group(12))
                pct_com = parse_latin_decimal(m.group(13))
                comision = parse_latin_decimal(m.group(14))
                neto_pagar = parse_latin_decimal(m.group(15))

                if cod_ag:
                    result["codigo_agencia_proveedor"] = cod_ag

                item = {
                    "fecha_emision": fecha_em,
                    "numero_factura": "",
                    "numero_boleto": tkt_no,
                    "pasajero": pax,
                    "aerolinea": airline,
                    "fecha_vuelo": None,
                    "ruta_itinerario": "",
                    "monto_fare": fare,
                    "monto_tax": tax,
                    "monto_subtotal": subtotal,
                    "monto_fee": fee,
                    "porcentaje_comision": pct_com,
                    "monto_comision": comision,
                    "monto_neto_pagar": neto_pagar,
                    "remarks": "",
                }
                result["items"].append(item)

        if result["items"]:
            fechas = [i["fecha_emision"] for i in result["items"] if i["fecha_emision"]]
            if fechas:
                fechas.sort()
                result["fecha_reporte_desde"] = fechas[0]
                result["fecha_reporte_hasta"] = fechas[-1]

        return result

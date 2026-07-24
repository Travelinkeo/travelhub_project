import io
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

import pypdf

from .base_parser import BaseSupplierReportParser

logger = logging.getLogger(__name__)


def parse_decimal(val_str: str) -> Decimal:
    if not val_str:
        return Decimal("0.00")
    clean = val_str.replace(",", "").strip()
    try:
        return Decimal(clean)
    except Exception:
        return Decimal("0.00")


def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


class CTGReportParser(BaseSupplierReportParser):
    def parse(self) -> dict[str, Any]:
        reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes))
        full_text = "\n".join([page.extract_text() or "" for page in reader.pages])

        result: dict[str, Any] = {
            "proveedor_nombre": "CTG",
            "codigo_agencia_proveedor": "",
            "fecha_reporte_desde": None,
            "fecha_reporte_hasta": None,
            "saldo_anterior": Decimal("0.00"),
            "monto_total_ventas": Decimal("0.00"),
            "saldo_final": Decimal("0.00"),
            "items": [],
            "raw_text": full_text,
        }

        client_no_match = re.search(r"Client No:\s*(\w+)", full_text, re.IGNORECASE)
        if client_no_match:
            result["codigo_agencia_proveedor"] = client_no_match.group(1).strip()

        from_to_match = re.search(
            r"From:\s*(\d{1,2}/\d{1,2}/\d{4})\s+To:\s*(\d{1,2}/\d{1,2}/\d{4})",
            full_text,
            re.IGNORECASE,
        )
        if from_to_match:
            result["fecha_reporte_desde"] = parse_date(from_to_match.group(1))
            result["fecha_reporte_hasta"] = parse_date(from_to_match.group(2))

        beg_bal = re.search(r"Beginning Balance\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if beg_bal:
            result["saldo_anterior"] = parse_decimal(beg_bal.group(1))

        tot_open = re.search(r"Total Open\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if tot_open:
            result["monto_total_ventas"] = parse_decimal(tot_open.group(1))

        acc_bal = re.search(r"Account Balance\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if acc_bal:
            result["saldo_final"] = parse_decimal(acc_bal.group(1))

        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        current_issue_dt = None
        current_invoice_no = ""

        # Patrón para boletos CTG: Ticket, (Pax + Vendor), Fecha Vuelo, Ruta, Monto
        row_regex = re.compile(
            r"^(\d{8,14})\s+(.+?)\s+(\d{1,2}/\d{1,2}/\d{4})\s+([A-Z]{6})\s+([\d\.\,-]+)$"
        )
        batch_pattern = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4})\s+(\d+)$")
        fee_pattern = re.compile(
            r"^([A-Z0-9\s\/]+?)\s+SERVICE FEE\s+([\d\.\,-]+)(.*)$", re.IGNORECASE
        )

        for line in lines:
            m_batch = batch_pattern.match(line)
            if m_batch:
                current_issue_dt = parse_date(m_batch.group(1))
                current_invoice_no = m_batch.group(2)
                continue

            m_tkt = row_regex.match(line)
            if m_tkt:
                tkt_no = m_tkt.group(1).strip()
                middle_str = m_tkt.group(2).strip()
                start_dt = parse_date(m_tkt.group(3))
                itin = m_tkt.group(4).strip()
                fare = parse_decimal(m_tkt.group(5))

                # Separar Pasajero y Vendor del bloque del medio
                # Las aerolíneas típicas de CTG son 'Laser Airlines', 'JET LINK EXPR', 'ESTELAR LATI', 'AVIOR AIRLINES', etc.
                known_vendors = [
                    "Laser Airlines",
                    "JET LINK EXPR",
                    "ESTELAR LATI",
                    "AVIOR AIRLINES",
                    "RUTACA AIRLINES",
                ]
                vendor = ""
                pax = middle_str

                for kv in known_vendors:
                    if kv.lower() in middle_str.lower():
                        idx = middle_str.lower().rfind(kv.lower())
                        pax = middle_str[:idx].strip()
                        vendor = middle_str[idx:].strip()
                        break

                if not vendor:
                    # Fallback: las últimas 2 palabras corresponden a la aerolínea
                    parts = middle_str.rsplit(maxsplit=2)
                    if len(parts) >= 3:
                        pax = parts[0]
                        vendor = f"{parts[1]} {parts[2]}"
                    else:
                        pax = middle_str
                        vendor = "AIRLINE"

                item = {
                    "fecha_emision": current_issue_dt,
                    "numero_factura": current_invoice_no,
                    "numero_boleto": tkt_no,
                    "pasajero": pax,
                    "aerolinea": vendor,
                    "fecha_vuelo": start_dt,
                    "ruta_itinerario": itin,
                    "monto_fare": fare,
                    "monto_tax": Decimal("0.00"),
                    "monto_subtotal": fare,
                    "monto_fee": Decimal("0.00"),
                    "porcentaje_comision": Decimal("0.00"),
                    "monto_comision": Decimal("0.00"),
                    "monto_neto_pagar": fare,
                    "remarks": "",
                }
                result["items"].append(item)
                continue

            m_fee = fee_pattern.match(line)
            if m_fee:
                pax = m_fee.group(1).strip()
                fee_val = parse_decimal(m_fee.group(2))
                remarks = m_fee.group(3).strip() if m_fee.group(3) else "SERVICE FEE"

                item = {
                    "fecha_emision": current_issue_dt,
                    "numero_factura": current_invoice_no,
                    "numero_boleto": "FEE-" + (current_invoice_no or "0"),
                    "pasajero": pax,
                    "aerolinea": "CTG SERVICE FEE",
                    "fecha_vuelo": None,
                    "ruta_itinerario": "",
                    "monto_fare": Decimal("0.00"),
                    "monto_tax": Decimal("0.00"),
                    "monto_subtotal": Decimal("0.00"),
                    "monto_fee": fee_val,
                    "porcentaje_comision": Decimal("0.00"),
                    "monto_comision": Decimal("0.00"),
                    "monto_neto_pagar": fee_val,
                    "remarks": remarks,
                }
                result["items"].append(item)
                continue

        return result

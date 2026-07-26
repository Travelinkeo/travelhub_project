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
    """Convierte string numérico (ej. 1,003.48 o -1,655.78) a Decimal de Python"""
    if not val_str:
        return Decimal("0.00")
    clean = val_str.replace(",", "").strip()
    try:
        return Decimal(clean)
    except Exception:
        return Decimal("0.00")


def parse_date(date_str: str) -> str | None:
    """Convierte fecha M/D/YYYY a YYYY-MM-DD"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


class CTGReportParser(BaseSupplierReportParser):
    """
    Parser especializado para reportes 'Client Statement' de CTG (Grupo Soporte Global Inc).
    """

    def parse(self) -> dict[str, Any]:
        """parse."""
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

        # 1. Extraer Metadatos
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

        # 2. Extraer Totales al Pie
        beg_bal = re.search(r"Beginning Balance\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if beg_bal:
            result["saldo_anterior"] = parse_decimal(beg_bal.group(1))

        tot_open = re.search(r"Total Open\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if tot_open:
            result["monto_total_ventas"] = parse_decimal(tot_open.group(1))

        acc_bal = re.search(r"Account Balance\s+([\d\.\,-]+)", full_text, re.IGNORECASE)
        if acc_bal:
            result["saldo_final"] = parse_decimal(acc_bal.group(1))

        # 3. Procesar Líneas del Reporte
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        current_issue_dt = None
        current_invoice_no = ""

        # Patrón para boletos CTG: Boleto, Pasajero, Aerolínea, Fecha Vuelo, Ruta, Monto
        # Ej: 0340943235 MARTINEZ/DIN Laser Airlines 4/9/2026 CURCCS 307.69
        ticket_pattern = re.compile(
            r"^(\d{8,14})\s+([A-Z0-9\s\/]+?)\s+([A-Za-z0-9\s\.\-]+?)\s+(\d{1,2}/\d{1,2}/\d{4})\s+([A-Z]{6})\s+([\d\.\,-]+)$"
        )
        # Patrón encabezado de lote: 3/3/2026 289289
        batch_pattern = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4})\s+(\d+)$")
        # Patrón para fees/comisiones: MARTINEZ/DIN SERVICE FEE -5.10 comision aerolineas
        fee_pattern = re.compile(
            r"^([A-Z0-9\s\/]+?)\s+SERVICE FEE\s+([\d\.\,-]+)(.*)$", re.IGNORECASE
        )

        for line in lines:
            # Revisa encabezado de fecha e invoice
            m_batch = batch_pattern.match(line)
            if m_batch:
                current_issue_dt = parse_date(m_batch.group(1))
                current_invoice_no = m_batch.group(2)
                continue

            # Revisa fila de boleto
            m_tkt = ticket_pattern.match(line)
            if m_tkt:
                tkt_no = m_tkt.group(1).strip()
                pax = m_tkt.group(2).strip()
                vendor = m_tkt.group(3).strip()
                start_dt = parse_date(m_tkt.group(4))
                itin = m_tkt.group(5).strip()
                fare = parse_decimal(m_tkt.group(6))

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

            # Revisa fila de Service Fee / Comisión suplementaria
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

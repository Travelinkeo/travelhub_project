import datetime
import re
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.bookings.models import SegmentoVuelo, Venta
from apps.common.services.catalog_service import CatalogNormalizationService
from apps.common.services.customer_service import CustomerService
from apps.crm.models import Pasajero
from core.api import agency_context


class PNRParserService:
    """
    Motor Autónomo de Extracción y Normalización de PNR crípticos.
    Soporta estructuras nativas de Amadeus, Sabre y KIU.
    """

    @classmethod
    def detectar_gds(cls, raw_text: str) -> str:
        """Identifica la firma del sistema de distribución global (GDS)."""
        if not raw_text:
            return "GENERIC"
        text_upper = raw_text.upper()
        if "RP/" in raw_text or "AMADEUS" in text_upper:
            return "AMADEUS"
        if "1." in raw_text and (
            "SABRE" in text_upper or re.search(r"\b[A-Z]{6}\b\s+\d{2}[A-Z]{3}\b", raw_text)
        ):
            return "SABRE"
        if "KIU" in text_upper or "KLR/" in raw_text:
            return "KIU"
        return "GENERIC"

    @classmethod
    def parse_to_dict(cls, raw_text: str) -> dict:
        """Punto de entrada: analiza el texto y retorna un diccionario normalizado."""
        gds = cls.detectar_gds(raw_text)

        pnr_data = {
            "gds": gds,
            "localizador": None,
            "pasajeros": [],
            "vuelos": [],
            "tarifa_total": Decimal("0.00"),
            "moneda": "USD",
        }

        if not raw_text:
            return pnr_data

        text_upper = raw_text.upper()

        # 1. Extraer Localizador / PNR
        if gds == "AMADEUS":
            loc_match = re.search(r"RP/[^\n]+?\b([A-Z0-9]{6})\s*$", raw_text, re.MULTILINE)
            if not loc_match:
                loc_match = re.search(r"RP/([A-Z0-9]{6})", raw_text)
            if not loc_match:
                loc_match = re.search(r"RP/[^\n]+?\b([A-Z0-9]{6})\b", raw_text)
            if loc_match:
                pnr_data["localizador"] = loc_match.group(1)

        elif gds == "SABRE":
            loc_match = re.search(r"\b([A-Z0-9]{6})\b\s+\-\s+SABRE", raw_text)
            if not loc_match:
                loc_match = re.search(r"RECORD LOCATOR\s+([A-Z0-9]{6})", text_upper)
            if loc_match:
                pnr_data["localizador"] = loc_match.group(1)

        elif gds == "KIU":
            loc_match = re.search(r"(?:KIU|KLR/)\s*([A-Z0-9]{6})", text_upper)
            if loc_match:
                pnr_data["localizador"] = loc_match.group(1)

        # Fallback de Localizador Genérico
        if not pnr_data["localizador"]:
            pnr_match = re.search(
                r"(?:RESERVACI[OÓ]N|RESERVA|CODE|PNR|LOCALIZADOR|RECORD|BOOKING REF)[:\s\n\-]+([A-Z0-9]{6})",
                text_upper,
            )
            if pnr_match:
                pnr_data["localizador"] = pnr_match.group(1)
            else:
                # Búsqueda libre de código de 6 caracteres alfanuméricos
                free_match = re.search(r"\b([A-Z0-9]{6})\b", text_upper)
                if free_match and not any(
                    m in free_match.group(1)
                    for m in [
                        "JAN",
                        "FEB",
                        "MAR",
                        "APR",
                        "MAY",
                        "JUN",
                        "JUL",
                        "AUG",
                        "SEP",
                        "OCT",
                        "NOV",
                        "DEC",
                    ]
                ):
                    pnr_data["localizador"] = free_match.group(1)

        # 2. Extraer Pasajeros
        # Formato común: 1.ALEMAN/JOSE ARMANDO, 2.SMITH/JOHN MR
        pasajeros_matches = re.findall(
            r"(?:^|\n)\s*\d+[\.\s]+([A-Z\s\-\']+)/([A-Z\s\-\'\+]+)", text_upper
        )
        for item in pasajeros_matches:
            # Limpiar nombre
            raw_name = item[1].strip()
            # Remover títulos
            clean_name = re.split(
                r"\s+(?:FOID|RIF|DNI|DOCUMENTO|DOC|TKTN|C\.I|V-|ADDRESS|TEL|PHONE|IATA|ISSUING|AGENTE|OFFICE|ID)\b",
                raw_name,
                flags=re.IGNORECASE,
            )[0]
            clean_name = re.sub(
                r"\b(?:MR|MRS|MS|MSTR|CHD)\b", "", clean_name, flags=re.IGNORECASE
            ).strip()

            pnr_data["pasajeros"].append({"apellido": item[0].strip(), "nombre": clean_name})

        # 3. Extraer Segmentos Aéreos
        # Patrón robusto para segmentos de vuelo:
        # AA 935 Y 15OCT CCSMIA HK1 0815 1145
        flight_pattern = re.compile(
            r"(?:\d+\s+)?"  # Index opcional (1 )
            r"([A-Z0-9]{2})\s*"  # Aerolinea (AV)
            r"(\d{1,4})\s*"  # Numero de vuelo (46)
            r"([A-Z])?\s*"  # Clase (C) opcional
            r"(\d{1,2}[A-Z]{3})\s+"  # Fecha (22MAY)
            r"(?:\d\s+)?"  # Día de semana opcional (4 )
            r"([A-Z]{3})\s*([A-Z]{3})\s+"  # Origen y Destino (BOGMAD o BOG MAD)
            r"([A-Z0-9]{2,3})\s+"  # Status (HK1)
            r"(\d{4}[A-Z]?)\s+"  # Salida (0700A)
            r"(\d{4}[A-Z]?(?:\+\d|\*\d)?|(?:\+\d)?)"  # Llegada (2330P o 2330+1)
        )

        # Pre-limpieza para evitar líneas de ruido
        lines = text_upper.splitlines()
        clean_lines = [
            l.strip()
            for l in lines
            if not any(
                x in l.strip()
                for x in [
                    "VIEWTRIP",
                    "CHECK-IN",
                    "BAGGAGE",
                    "EQUIPAJE",
                    "URL",
                    "HTTPS",
                    "CO2",
                    "EMISSION",
                    "OPERATED BY",
                ]
            )
        ]
        text_for_flights = "\n".join(clean_lines)

        flight_matches = flight_pattern.findall(text_for_flights)
        for flight in flight_matches:
            # Normalizar horas (0700A -> 07:00, 2330 -> 23:30)
            def norm_h(h):
                h = re.sub(r"[A-Z\+\*\d]", "", h)  # Limpiar letras y offsets
                if len(h) == 4:
                    return f"{h[:2]}:{h[2:]}"
                return h

            dep_time = norm_h(flight[7])
            arr_time = norm_h(flight[8])

            pnr_data["vuelos"].append(
                {
                    "aerolinea": flight[0],
                    "numero_vuelo": f"{flight[0]} {flight[1]}",
                    "clase": flight[2],
                    "fecha_salida": flight[3],  # Ej: 15OCT
                    "origen": flight[4],
                    "destino": flight[5],
                    "status": flight[6],
                    "hora_salida": dep_time,
                    "hora_llegada": arr_time,
                }
            )

        # 4. Extraer Tarifa Total y Moneda
        fare_patterns = [
            r"(?:TOTAL|FARE|TARIFA|NETO)\s*(?:FARE|TOTAL|AMOUNT)?\s*(?:[A-Z]{3})?\s*([0-9]{1,3}(?:[.,\s][0-9]{3})*[.,][0-9]{2})\b",
            r"\b([A-Z]{3})\s*([0-9]{1,3}(?:[.,\s][0-9]{3})*[.,][0-9]{2})\b",
        ]

        cur_match = re.search(r"\b(USD|VES|EUR|COP|ARS|MXN|BRL|CLP|PEN)\b", text_upper)
        if cur_match:
            pnr_data["moneda"] = cur_match.group(1)

        for pattern in fare_patterns:
            matches = re.finditer(pattern, text_upper)
            for match in matches:
                try:
                    val_str = match.group(match.lastindex)
                    val_str = val_str.replace(" ", "").replace(",", "")
                    val_dec = Decimal(val_str)
                    if val_dec > pnr_data["tarifa_total"]:
                        pnr_data["tarifa_total"] = val_dec
                except Exception:
                    pass

        return pnr_data

    @classmethod
    @transaction.atomic
    def ingerir_pnr_en_db(cls, raw_text: str, agencia, usuario=None) -> Venta:
        """
        Procesa el PNR crudo y ejecuta la creación atómica en la base de datos PostgreSQL
        respetando estrictamente el aislamiento Multi-Tenant de la Agencia.
        """
        with agency_context(agencia):
            data = cls.parse_to_dict(raw_text)

            if not data["localizador"]:
                raise ValueError(
                    "No se pudo extraer un localizador de reserva válido del PNR proporcionado."
                )

            # Identificar o crear el Cliente pagador asociado a la venta
            first_pax = data["pasajeros"][0] if data["pasajeros"] else None
            pax_data = {}
            if first_pax:
                pax_data["passenger_name"] = f"{first_pax['apellido']}/{first_pax['nombre']}"
            else:
                pax_data["passenger_name"] = "PASAJERO GDS"

            cliente = CustomerService.identify_or_create(pax_data, agencia)
            moneda_obj = CatalogNormalizationService.normalize_currency(data["moneda"])

            # 1. Crear o recuperar la entidad Venta
            venta, created = Venta.objects.get_or_create(
                localizador=data["localizador"],
                agencia=agencia,
                defaults={
                    "cliente": cliente,
                    "creado_por": usuario,
                    "moneda": moneda_obj,
                    "canal_origen": Venta.CanalOrigen.API,
                    "fecha_venta": timezone.now(),
                    "subtotal": data["tarifa_total"],
                    "impuestos": Decimal("0.00"),
                },
            )

            # Si ya existía, actualizamos sus montos financieros si son cero
            if not created and venta.subtotal == Decimal("0.00"):
                venta.subtotal = data["tarifa_total"]
                venta.save(update_fields=["subtotal"])

            # 2. Ingestión del CRM: Registrar Pasajeros
            for psgr in data["pasajeros"]:
                pasajero, _ = Pasajero.objects.get_or_create(
                    agencia=agencia,
                    nombres=psgr["nombre"][:100],
                    apellidos=psgr["apellido"][:100],
                )
                venta.pasajeros.add(pasajero)

            # 3. Registrar los Tramos de Vuelo
            for flight in data["vuelos"]:
                origen_city = CatalogNormalizationService.get_or_create_ciudad_by_iata(
                    flight["origen"]
                )
                destino_city = CatalogNormalizationService.get_or_create_ciudad_by_iata(
                    flight["destino"]
                )

                fecha_salida = cls._parse_date_flexible(flight["fecha_salida"], venta.fecha_venta)
                fecha_llegada = None

                if fecha_salida:
                    try:
                        dep_hour, dep_min = map(int, flight["hora_salida"].split(":"))
                        arr_hour, arr_min = map(int, flight["hora_llegada"].split(":"))

                        dt_salida = fecha_salida.replace(hour=dep_hour, minute=dep_min)
                        fecha_salida = dt_salida

                        dt_llegada = fecha_salida.replace(hour=arr_hour, minute=arr_min)
                        if dt_llegada < dt_salida:
                            dt_llegada += datetime.timedelta(days=1)
                        fecha_llegada = dt_llegada
                    except Exception:
                        fecha_llegada = fecha_salida

                SegmentoVuelo.objects.get_or_create(
                    venta=venta,
                    agencia=agencia,
                    origen=origen_city,
                    destino=destino_city,
                    aerolinea=flight["aerolinea"],
                    numero_vuelo=flight["numero_vuelo"],
                    defaults={
                        "fecha_salida": fecha_salida,
                        "fecha_llegada": fecha_llegada,
                        "clase_reserva": flight.get("clase"),
                        "cabina": "ECONOMY",
                    },
                )

            # Gatillamos la tarea asíncrona de cumplimiento inmediatamente
            from apps.bookings.tasks import verificar_cumplimiento_pasaportes_reserva_task

            transaction.on_commit(
                lambda: verificar_cumplimiento_pasaportes_reserva_task.delay(
                    venta.pk, agencia_id=venta.agencia_id
                )
            )

            return venta

    @classmethod
    def _parse_date_flexible(
        cls, date_str: str, base_date: datetime.datetime = None
    ) -> datetime.datetime:
        """Parsea una cadena como '22MAY' o '22MAY26' resolviendo el año de forma proactiva."""
        if not date_str:
            return None

        date_str = date_str.strip().upper()
        if not base_date:
            base_date = timezone.now()

        months = {
            "JAN": 1,
            "FEB": 2,
            "MAR": 3,
            "APR": 4,
            "MAY": 5,
            "JUN": 6,
            "JUL": 7,
            "AUG": 8,
            "SEP": 9,
            "OCT": 10,
            "NOV": 11,
            "DEC": 12,
            "ENE": 1,
            "ABR": 4,
            "AGO": 8,
            "DIC": 12,
        }

        # Con año
        match_with_year = re.match(r"(\d{1,2})\s*([A-Z]{3})\s*(\d{2,4})", date_str)
        if match_with_year:
            day = int(match_with_year.group(1))
            month_name = match_with_year.group(2)
            year_val = match_with_year.group(3)
            year = 2000 + int(year_val) if len(year_val) == 2 else int(year_val)
            month = months.get(month_name, 1)
            try:
                return timezone.make_aware(datetime.datetime(year, month, day))
            except Exception:
                return None

        # Sin año
        match_no_year = re.match(r"(\d{1,2})\s*([A-Z]{3})", date_str)
        if match_no_year:
            day = int(match_no_year.group(1))
            month_name = match_no_year.group(2)
            month = months.get(month_name, 1)
            year = base_date.year

            if month < base_date.month:
                year += 1

            try:
                return timezone.make_aware(datetime.datetime(year, month, day))
            except Exception:
                return None
        return None

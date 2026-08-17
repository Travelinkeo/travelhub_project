import logging
import re
from hashlib import sha256

from django.db import models


# Helper functions to avoid circular imports during module loading
def get_cliente_model():
    """get_cliente_model."""
    from django.apps import apps

    return apps.get_model("crm", "Cliente")


def get_pasajero_model():
    """get_pasajero_model."""
    from django.apps import apps

    return apps.get_model("crm", "Pasajero")


logger = logging.getLogger(__name__)


class CustomerService:
    """CustomerService."""

    @staticmethod
    def _clean_string(text):
        if not text:
            return ""
        # Remover "(Auto-Generado)" o "(Auto-Generado)." o puntos aislados
        s = re.sub(r"\(Auto-Generado\)\.?", "", str(text), flags=re.IGNORECASE)
        s = re.sub(r"\(Sin Apellido\)", "", s, flags=re.IGNORECASE)
        s = s.strip(" .\t\r\n")
        return s

    @classmethod
    def _parse_names(cls, data):
        """
        Extrae nombres y apellidos limpios de los múltiples formatos del parser (GDS, KIU, Sabre, Amadeus).
        """
        if not isinstance(data, dict):
            full = str(data or "").strip()
            data = {"passenger_name": full}

        first = cls._clean_string(
            data.get("first_name")
            or data.get("solo_nombre_pasajero")
            or data.get("SOLO_NOMBRE_PASAJERO")
        )
        last = cls._clean_string(data.get("last_name"))
        full = cls._clean_string(
            data.get("passenger_name")
            or data.get("NOMBRE_DEL_PASAJERO")
            or data.get("nombre_pasajero")
            or data.get("human_name")
            or data.get("PASAJERO")
            or ""
        )

        if first and last:
            return first.title(), last.title()

        if "/" in full:
            parts = full.split("/")
            apellidos = cls._clean_string(parts[0]).title()
            nombres = cls._clean_string(parts[1]).title() if len(parts) > 1 else ""
            if not nombres:
                nombres = "Pasajero"
            return nombres, apellidos
        elif "," in full:
            parts = full.split(",")
            apellidos = cls._clean_string(parts[0]).title()
            nombres = cls._clean_string(parts[1]).title() if len(parts) > 1 else ""
            if not nombres:
                nombres = "Pasajero"
            return nombres, apellidos
        elif full:
            words = full.split()
            if len(words) == 1:
                return words[0].title(), ""
            elif len(words) == 2:
                return words[0].title(), words[1].title()
            else:
                # E.g. "Alex Duque Echeverri" -> Nombres: "Alex", Apellidos: "Duque Echeverri"
                return words[0].title(), " ".join(words[1:]).title()

        return "Pasajero", ""

    @staticmethod
    def _extract_document_info(data):
        """
        Extrae y normaliza el documento de identidad / pasaporte según GDS (KIU, Sabre, Amadeus, Web).
        Formatos soportados:
          - IDVCI24557367 -> DNI, V-24557367, VE
          - IDECI12345678 -> DNI, E-12345678
          - IDVP12345678 / IDVPP... -> PASS, 12345678, VE
          - IDEP12345678 / IDEPP... -> PASS, 12345678
          - NIV24557367 / NI24557367 -> DNI, V-24557367, VE
          - NIE12345678 -> DNI, E-12345678
          - V-24557367 / V24557367 / CI24557367 -> DNI, V-24557367, VE
          - E-12345678 / E12345678 -> DNI, E-12345678
          - FOID / PP / PASS / Amadeus / Sabre / Pasaporte internacional
        """
        if not isinstance(data, dict):
            return None, None, None, None, "PASS", None

        doc_raw = (
            data.get("passenger_document")
            or data.get("foid")
            or data.get("CODIGO_IDENTIFICACION")
            or data.get("codigo_identificacion")
            or data.get("customerNumber")
            or data.get("ID_PASAJERO")
            or ""
        )
        if not doc_raw:
            return None, None, None, None, "PASS", None

        doc_str = str(doc_raw).strip()
        doc_clean = re.sub(r"[^A-Za-z0-9]", "", doc_str).upper()
        if not doc_clean:
            return None, None, None, None, "PASS", None

        doc_hash = sha256(doc_clean.encode()).hexdigest()

        tipo_doc = "PASS"
        cedula = None
        pasaporte = None
        pais_iso = None

        # 1. KIU en Dólares / Nacional / Internacional:
        # IDVCI -> ID + V (Venezolana) + CI (Cédula de Identidad)
        m_idvci = re.match(r"^IDVCI(\d+)$", doc_clean)
        if m_idvci:
            tipo_doc = "DNI"
            cedula = f"V-{m_idvci.group(1)}"
            pais_iso = "VE"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        # IDECI -> ID + E (Extranjero) + CI (Cédula de Identidad)
        m_ideci = re.match(r"^IDECI(\d+)$", doc_clean)
        if m_ideci:
            tipo_doc = "DNI"
            cedula = f"E-{m_ideci.group(1)}"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        # IDVP / IDVPP -> ID + V (Venezolana) + P (Pasaporte)
        m_idvp = re.match(r"^IDVP+([A-Z0-9]+)$", doc_clean)
        if m_idvp:
            tipo_doc = "PASS"
            pasaporte = m_idvp.group(1)
            pais_iso = "VE"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        # IDEP / IDEPP -> ID + E (Extranjero) + P (Pasaporte)
        m_idep = re.match(r"^IDEP+([A-Z0-9]+)$", doc_clean)
        if m_idep:
            tipo_doc = "PASS"
            pasaporte = m_idep.group(1)
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        # 2. Web Aerolíneas (Formato NI / National ID)
        m_niv = re.match(r"^NIV(\d+)$", doc_clean)
        if m_niv:
            tipo_doc = "DNI"
            cedula = f"V-{m_niv.group(1)}"
            pais_iso = "VE"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        m_nie = re.match(r"^NIE(\d+)$", doc_clean)
        if m_nie:
            tipo_doc = "DNI"
            cedula = f"E-{m_nie.group(1)}"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        m_ni = re.match(r"^NI(\d+)$", doc_clean)
        if m_ni:
            tipo_doc = "DNI"
            cedula = f"V-{m_ni.group(1)}"
            pais_iso = "VE"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        # 3. Formato Directo Cédula Venezolana / Extranjera
        m_v = re.match(r"^(?:V|CI)(\d+)$", doc_clean)
        if m_v:
            tipo_doc = "DNI"
            cedula = f"V-{m_v.group(1)}"
            pais_iso = "VE"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        m_e = re.match(r"^E(\d+)$", doc_clean)
        if m_e:
            tipo_doc = "DNI"
            cedula = f"E-{m_e.group(1)}"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        # 4. Solo dígitos hasta 9 caracteres (Típicamente Cédula Venezolana)
        if doc_clean.isdigit() and len(doc_clean) <= 9:
            tipo_doc = "DNI"
            cedula = f"V-{doc_clean}"
            pais_iso = "VE"
            return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

        # 5. Pasaportes internacionales / Sabre / Amadeus / FOID
        num_clean = re.sub(r"^(?:FOID|PP|PASS|PASSPORT)", "", doc_clean)
        pasaporte = num_clean if num_clean else doc_clean
        tipo_doc = "PASS"

        return doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso

    @classmethod
    def identify_or_create(cls, data, agencia, forced_cliente_id=None):
        """
        Identifica un cliente existente por ID, documento/hash o nombre, o crea uno nuevo de forma deduplicada.
        """
        Cliente = get_cliente_model()
        cliente = None
        if forced_cliente_id:
            try:
                cliente = Cliente.objects.get(pk=forced_cliente_id)
            except Cliente.DoesNotExist:
                pass

        if not cliente:
            nombres, apellidos = cls._parse_names(data)
            doc_clean, doc_hash, cedula, pasaporte, _, pais_iso = cls._extract_document_info(data)

            # 1. Búsqueda por Documento / Hash (Máxima Prioridad)
            if doc_hash or doc_clean:
                q_doc = models.Q()
                if doc_hash:
                    q_doc |= models.Q(documento_hash=doc_hash)
                if cedula:
                    q_doc |= models.Q(cedula_identidad__iexact=cedula)
                if pasaporte:
                    q_doc |= models.Q(numero_pasaporte__iexact=pasaporte)
                if doc_clean:
                    q_doc |= models.Q(cedula_identidad__iexact=doc_clean) | models.Q(
                        numero_pasaporte__iexact=doc_clean
                    )

                cliente = Cliente.objects.filter(agencia=agencia).filter(q_doc).first()

            # 2. Búsqueda por Nombre y Apellido (Fallback)
            if not cliente and nombres:
                q_name = models.Q(agencia=agencia, nombres__iexact=nombres)
                if apellidos:
                    q_name &= models.Q(apellidos__iexact=apellidos)
                cliente = Cliente.objects.filter(q_name).first()

            # 3. Creación Atómica Deduplicada
            if not cliente:
                email = data.get("email") or ""
                telefono = (
                    data.get("telefono")
                    or data.get("phone")
                    or data.get("telefono_principal")
                    or ""
                )

                cliente = Cliente.objects.create(
                    agencia=agencia,
                    nombres=nombres,
                    apellidos=apellidos or "",
                    cedula_identidad=cedula or (doc_clean if not pasaporte else None),
                    numero_pasaporte=pasaporte,
                    documento_hash=doc_hash or "",
                    email=email,
                    telefono_principal=telefono,
                    tipo_cliente="IND",
                )
                logger.info(
                    f"👤 Cliente creado: {cliente.get_nombre_completo()} ({cliente.cedula_identidad or cliente.numero_pasaporte or 'Sin Doc'})"
                )
            else:
                # Actualizar campos que puedan estar vacíos en el cliente existente
                updated = False
                if not cliente.cedula_identidad and (cedula or doc_clean):
                    cliente.cedula_identidad = cedula or doc_clean
                    updated = True
                if not cliente.numero_pasaporte and pasaporte:
                    cliente.numero_pasaporte = pasaporte
                    updated = True
                if not cliente.documento_hash and doc_hash:
                    cliente.documento_hash = doc_hash
                    updated = True
                if not cliente.email and data.get("email"):
                    cliente.email = data.get("email")
                    updated = True
                if not cliente.telefono_principal and (data.get("telefono") or data.get("phone")):
                    cliente.telefono_principal = data.get("telefono") or data.get("phone")
                    updated = True
                if updated:
                    cliente.save()

        return cliente

    @classmethod
    def sync_pasajero(cls, data, agencia, venta):
        """
        Sincroniza el registro de Pasajero con todos sus datos migratorios y de identidad,
        vinculándolo tanto a la Venta como al grupo de pasajeros del Cliente titular.
        """
        Pasajero = get_pasajero_model()
        nombres, apellidos = cls._parse_names(data)
        doc_clean, doc_hash, cedula, pasaporte, tipo_doc, pais_iso = cls._extract_document_info(
            data
        )

        # 1. Búsqueda de Pasajero existente en la agencia
        pasajero = None
        if doc_hash or doc_clean:
            q_doc = models.Q()
            if doc_hash:
                q_doc |= models.Q(documento_hash=doc_hash)
            if cedula:
                q_doc |= models.Q(cedula_identidad__iexact=cedula)
            if pasaporte:
                q_doc |= models.Q(numero_pasaporte__iexact=pasaporte)
            if doc_clean:
                q_doc |= models.Q(cedula_identidad__iexact=doc_clean) | models.Q(
                    numero_pasaporte__iexact=doc_clean
                )

            pasajero = Pasajero.objects.filter(agencia=agencia).filter(q_doc).first()

        if not pasajero and nombres:
            q_name = models.Q(agencia=agencia, nombres__iexact=nombres)
            if apellidos:
                q_name &= models.Q(apellidos__iexact=apellidos)
            pasajero = Pasajero.objects.filter(q_name).first()

        email = data.get("email") if isinstance(data, dict) else None
        telefono = data.get("telefono") or data.get("phone") if isinstance(data, dict) else None

        # 2. Creación o Actualización Completa
        if not pasajero:
            pasajero = Pasajero.objects.create(
                agencia=agencia,
                nombres=nombres,
                apellidos=apellidos or "",
                cedula_identidad=cedula or (doc_clean if not pasaporte else None),
                numero_pasaporte=pasaporte,
                documento_hash=doc_hash or "",
                tipo_documento=tipo_doc,
                email=email,
                telefono=telefono,
            )
            logger.info(
                f"✈️ Pasajero creado: {pasajero.nombre_completo} (Doc: {pasajero.cedula_identidad or pasajero.numero_pasaporte or 'N/A'})"
            )
        else:
            # Enriquecer datos faltantes
            updated = False
            if (
                not pasajero.apellidos or pasajero.apellidos in (".", "(Sin Apellido)")
            ) and apellidos:
                pasajero.apellidos = apellidos
                updated = True
            if (not pasajero.nombres or "(Auto-Generado)" in pasajero.nombres) and nombres:
                pasajero.nombres = nombres
                updated = True
            if not pasajero.cedula_identidad and (cedula or doc_clean):
                pasajero.cedula_identidad = cedula or doc_clean
                updated = True
            if not pasajero.numero_pasaporte and pasaporte:
                pasajero.numero_pasaporte = pasaporte
                updated = True
            if not pasajero.documento_hash and doc_hash:
                pasajero.documento_hash = doc_hash
                updated = True
            if not pasajero.email and email:
                pasajero.email = email
                updated = True
            if not pasajero.telefono and telefono:
                pasajero.telefono = telefono
                updated = True
            if updated:
                pasajero.save()

        # Asignar País/Nacionalidad si se detectó y no está asignado
        if pais_iso and not pasajero.nacionalidad:
            try:
                from apps.common.models import Pais

                p_obj = Pais.objects.filter(codigo_iso_2=pais_iso).first()
                if p_obj:
                    pasajero.nacionalidad = p_obj
                    pasajero.save(update_fields=["nacionalidad"])
            except Exception as e_pais:
                logger.debug(f"No se pudo asignar país {pais_iso}: {e_pais}")

        # 3. Vincular a la Venta
        if venta:
            venta.pasajeros.add(pasajero)
            # 4. Vincular al grupo familiar/corporativo del Cliente titular
            if venta.cliente:
                venta.cliente.pasajeros.add(pasajero)

        return pasajero

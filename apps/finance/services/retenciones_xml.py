import logging
import xml.etree.ElementTree as ET
from decimal import Decimal

from defusedxml.minidom import parseString as minidom_parse_string

from apps.finance.models_stubs import RetencionISLR

logger = logging.getLogger(__name__)


class RetencionesXMLService:
    """
    Servicio para generar el archivo XML de Retenciones de ISLR para el portal del SENIAT.
    """

    @staticmethod
    def generar_xml_retenciones(fecha_inicio, fecha_fin, agencia):
        """
        Genera el archivo XML para la declaración mensual de retenciones de ISLR.
        """
        # Buscar retenciones del período
        retenciones = RetencionISLR.objects.filter(
            fecha_emision__gte=fecha_inicio,
            fecha_emision__lte=fecha_fin,
            agencia=agencia,
            estado=RetencionISLR.Estado.APLICADA,
        ).select_related("factura", "cliente")

        # RIF de la agencia/empresa que declara (Agente de Retención)
        rif_agente = agencia.rif or "J000000000"
        # Período fiscal en formato AAAAMM (ej: 202607)
        periodo = fecha_inicio.strftime("%Y%m")

        # Elemento Raíz
        root = ET.Element("RelacionRetencionesISLR")
        root.set("RifAgente", rif_agente)
        root.set("Periodo", periodo)

        for ret in retenciones:
            detalle = ET.SubElement(root, "DetalleRetencion")

            # Obtener RIF del retenido
            rif_retenido = ""
            if ret.factura and ret.factura.cliente_identificacion:
                rif_retenido = ret.factura.cliente_identificacion
            elif ret.cliente:
                rif_retenido = ret.cliente.cedula_identidad or ""

            # Limpiar caracteres no numéricos o prefijo de RIF
            rif_retenido = rif_retenido.replace("-", "").replace(" ", "").upper()

            num_factura = ret.factura.numero_factura if ret.factura else "N/A"
            num_control = ret.factura.numero_control if ret.factura else "00000000"
            fecha_op = ret.fecha_operacion or ret.fecha_emision
            codigo_concepto = ret.codigo_concepto or "001"
            base_imp = ret.base_imponible or Decimal("0.00")
            pct = ret.porcentaje_retencion or Decimal("0.00")

            # Elementos del detalle
            ET.SubElement(detalle, "RifRetenido").text = rif_retenido
            ET.SubElement(detalle, "NumeroFactura").text = num_factura
            ET.SubElement(detalle, "NumeroControl").text = num_control
            ET.SubElement(detalle, "FechaOperacion").text = fecha_op.strftime("%Y-%m-%d")
            ET.SubElement(detalle, "CodigoConcepto").text = codigo_concepto
            ET.SubElement(detalle, "MontoOperacion").text = f"{base_imp:.2f}"
            ET.SubElement(detalle, "PorcentajeRetencion").text = f"{pct:.2f}"

        # Convertir a XML string formateado
        xml_str = ET.tostring(root, encoding="utf-8")
        reparsed = minidom_parse_string(xml_str)
        return reparsed.toprettyxml(indent="    ")

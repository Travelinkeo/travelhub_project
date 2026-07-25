"""Servicio de analytics service para la aplicación common.
"""

import io
import logging
from typing import TYPE_CHECKING

import pandas as pd
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

if TYPE_CHECKING:
    pass


def __getattr__(name):
    if name == "Venta":
        from django.apps import apps

        return apps.get_model("bookings", "Venta")
    if name == "BoletoImportado":
        from django.apps import apps

        return apps.get_model("bookings", "BoletoImportado")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


User = get_user_model()
logger = logging.getLogger(__name__)


class AnalyticsService:
    """Servicio para analytics. Uso: instanciar según necesidad del dominio.
    """
    @staticmethod
    def get_ventas_mensuales(year=None):
        # get_ventas_mensuales: Obtiene/recupera ventas mensuales. Args: según implementación. Returns: dato solicitado.
        from django.apps import apps

        Venta = apps.get_model("bookings", "Venta")
        if not year:
            year = timezone.now().year

        # Filtrar ventas válidas (Pagadas o Completadas)
        qs = Venta.objects.filter(
            fecha_venta__year=year,
            estado__in=[
                Venta.EstadoVenta.PAGADA_TOTAL,
                Venta.EstadoVenta.COMPLETADA,
                Venta.EstadoVenta.CONFIRMADA,
            ],
        )

        # Agrupar por mes
        data = (
            qs.annotate(month=TruncMonth("fecha_venta"))
            .values("month")
            .annotate(total=Sum("total_venta"))
            .order_by("month")
        )

        # Formatear para Chart.js [Jan, Feb...]
        labels = []
        values = []
        for entry in data:
            if entry["month"] is not None:
                labels.append(entry["month"].strftime("%B"))
                values.append(float(entry["total"] or 0))

        return {"labels": labels, "values": values, "year": year}

    @staticmethod
    def get_top_vendedores(year=None, limit=5):
        # get_top_vendedores: Obtiene/recupera top vendedores. Args: según implementación. Returns: dato solicitado.
        from django.apps import apps

        Venta = apps.get_model("bookings", "Venta")
        if not year:
            year = timezone.now().year

        qs = Venta.objects.filter(
            fecha_venta__year=year,
            estado__in=[
                Venta.EstadoVenta.PAGADA_TOTAL,
                Venta.EstadoVenta.COMPLETADA,
                Venta.EstadoVenta.CONFIRMADA,
            ],
        )

        data = (
            qs.values("creado_por__username")
            .annotate(total=Sum("total_venta"))
            .order_by("-total")[:limit]
        )

        return list(data)

    @staticmethod
    def get_top_aerolineas(year=None, limit=5):
        # get_top_aerolineas: Obtiene/recupera top aerolineas. Args: según implementación. Returns: dato solicitado.
        from django.apps import apps

        BoletoImportado = apps.get_model("bookings", "BoletoImportado")
        if not year:
            year = timezone.now().year

        # Usamos BoletoImportado para obtener la aerolínea real
        # Filtramos boletos asociados a ventas válidas
        qs = (
            BoletoImportado.objects.filter(fecha_emision_boleto__year=year)
            .exclude(aerolinea_emisora__isnull=True)
            .exclude(aerolinea_emisora="")
        )

        # Agrupar por nombre de aerolínea
        # OJO: Los nombres pueden venir sucios ("Avianca", "AVIANCA S.A."), idealmente normalizar antes,
        # pero por ahora agrupamos raw.
        data = (
            qs.values("aerolinea_emisora")
            .annotate(count=Count("id_boleto_importado"), total_sales=Sum("total_boleto"))
            .order_by("-total_sales")[:limit]
        )

        # Convertir Decimal a float para JSON
        result = []
        for item in data:
            result.append(
                {
                    "aerolinea": item["aerolinea_emisora"],
                    "count": item["count"],
                    "total": float(item["total_sales"] or 0),
                }
            )

        return result

    @staticmethod
    def get_kpis_resumen(year=None):
        # get_kpis_resumen: Obtiene/recupera kpis resumen. Args: según implementación. Returns: dato solicitado.
        from django.apps import apps

        Venta = apps.get_model("bookings", "Venta")
        if not year:
            year = timezone.now().year

        Venta.objects.filter(fecha_venta__year=year)

    @staticmethod
    def get_aerolineas_disponibles(agencia):
        """
        Retorna una lista de aerolíneas únicas que tienen boletos importados para la agencia.
        """
        from django.apps import apps

        BoletoImportado = apps.get_model("bookings", "BoletoImportado")
        return (
            BoletoImportado.objects.filter(agencia=agencia)
            .exclude(aerolinea_emisora__isnull=True)
            .exclude(aerolinea_emisora="")
            .values_list("aerolinea_emisora", flat=True)
            .distinct()
            .order_by("aerolinea_emisora")
        )

    @staticmethod
    def get_reporte_comisiones_boletos(agencia, fecha_inicio=None, fecha_fin=None, aerolinea=None):
        """
        Genera un reporte detallado de producción y comisiones por boleto.
        """
        from django.apps import apps

        BoletoImportado = apps.get_model("bookings", "BoletoImportado")
        qs = BoletoImportado.objects.filter(agencia=agencia, estado_parseo="COM")

        if fecha_inicio:
            qs = qs.filter(fecha_emision_boleto__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_emision_boleto__lte=fecha_fin)
        if aerolinea:
            qs = qs.filter(aerolinea_emisora=aerolinea)

        # Totales Generales
        totales = qs.aggregate(
            total_boletos=Count("id_boleto_importado"),
            total_ventas=Sum("total_boleto"),
            total_comisiones=Sum("comision_agencia"),
            total_neto=Sum("tarifa_base"),
            total_pendiente=Sum("total_boleto", filter=Q(venta_asociada__isnull=True)),
        )

        # Desglose por Aerolínea
        por_aerolinea = (
            qs.values("aerolinea_emisora")
            .annotate(
                cantidad_boletos=Count("id_boleto_importado"),
                total_ventas=Sum("total_boleto"),
                total_comisiones=Sum("comision_agencia"),
            )
            .order_by("-total_comisiones")
        )

        # Lista Detallada (últimos 100 para la tabla)
        detalles = []
        for b in qs.order_by("-fecha_emision_boleto")[:100]:
            # Intentar extraer código de aerolínea para el logo
            aero_codigo = None
            if b.numero_boleto and len(b.numero_boleto) >= 3:
                # Opcional: Mapeo de prefijos numéricos a IATA (simplificado)
                prefijos = {
                    "134": "AV",
                    "230": "CM",
                    "045": "LA",
                    "001": "AA",
                    "057": "AF",
                    "074": "KL",
                    "239": "AT",
                }
                aero_codigo = prefijos.get(b.numero_boleto[:3])

            if not aero_codigo and b.datos_parseados:
                # Intentar desde los segmentos
                try:
                    import json

                    datos = b.datos_parseados
                    if isinstance(datos, str):
                        datos = json.loads(datos)
                    segmentos = datos.get("segmentos", [])
                    if segmentos and "vuelo" in segmentos[0]:
                        import re

                        match = re.match(r"^([A-Z0-9]{2,3})", str(segmentos[0]["vuelo"]))
                        if match:
                            aero_codigo = match.group(1)
                except Exception as e:
                    logger.warning(
                        f"No se pudo extraer codigo IATA desde segmentos para boleto {b.pk}: {e}"
                    )

            detalles.append(
                {
                    "fecha_emision": b.fecha_emision_boleto,
                    "numero_boleto": b.numero_boleto,
                    "pnr": b.localizador_pnr,
                    "pasajero_nombre": b.nombre_pasajero_procesado or b.nombre_pasajero_completo,
                    "aerolinea_nombre": b.aerolinea_emisora,
                    "aerolinea_codigo": aero_codigo or "XX",
                    "monto_neto": float(b.tarifa_base or 0),
                    "comision": float(b.comision_agencia or 0),
                    "total": float(b.total_boleto or 0),
                    "estado": "Auditado" if b.venta_asociada else "Pendiente",
                }
            )

        return {
            "totales": {
                "total_boletos": totales["total_boletos"] or 0,
                "total_ventas": float(totales["total_ventas"] or 0),
                "total_comisiones": float(totales["total_comisiones"] or 0),
                "total_neto": float(totales["total_neto"] or 0),
                "total_pendiente": float(totales["total_pendiente"] or 0),
            },
            "por_aerolinea": [
                {
                    "aerolinea": item["aerolinea_emisora"] or "Desconocida",
                    "cantidad_boletos": item["cantidad_boletos"],
                    "total_ventas": float(item["total_ventas"] or 0),
                    "total_comisiones": float(item["total_comisiones"] or 0),
                }
                for item in por_aerolinea
            ],
            "boletos": detalles,
        }

    @staticmethod
    def exportar_reporte_boletos_excel(agencia, fecha_inicio=None, fecha_fin=None, aerolinea=None):
        """
        Exporta el reporte de boletos a un archivo Excel con múltiples pestañas.
        """
        from django.apps import apps

        BoletoImportado = apps.get_model("bookings", "BoletoImportado")
        reporte = AnalyticsService.get_reporte_comisiones_boletos(
            agencia, fecha_inicio, fecha_fin, aerolinea
        )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # 1. Resumen General
            resumen_data = {
                "Métrica": [
                    "Total Boletos",
                    "Total Ventas",
                    "Total Neto",
                    "Total Comisiones",
                    "Total Pendiente",
                ],
                "Valor": [
                    reporte["totales"]["total_boletos"],
                    reporte["totales"]["total_ventas"],
                    reporte["totales"]["total_neto"],
                    reporte["totales"]["total_comisiones"],
                    reporte["totales"]["total_pendiente"],
                ],
            }
            pd.DataFrame(resumen_data).to_excel(writer, sheet_name="Resumen", index=False)

            # 2. Por Aerolínea
            if reporte["por_aerolinea"]:
                df_aerolinea = pd.DataFrame(reporte["por_aerolinea"])
                df_aerolinea.columns = [
                    "Aerolínea",
                    "Cant. Boletos",
                    "Total Ventas",
                    "Total Comisiones",
                ]
                df_aerolinea.to_excel(writer, sheet_name="Por Aerolinea", index=False)

            # 3. Listado Detallado (Aquí exportamos todos, no solo los últimos 100)
            # Re-calculamos el QS para tener todos los datos sin el slice de 100
            qs = BoletoImportado.objects.filter(agencia=agencia, estado_parseo="COM")
            if fecha_inicio:
                qs = qs.filter(fecha_emision_boleto__gte=fecha_inicio)
            if fecha_fin:
                qs = qs.filter(fecha_emision_boleto__lte=fecha_fin)
            if aerolinea:
                qs = qs.filter(aerolinea_emisora=aerolinea)

            detalles_full = []
            for b in qs.order_by("-fecha_emision_boleto"):
                detalles_full.append(
                    {
                        "Fecha Emisión": b.fecha_emision_boleto,
                        "Número Boleto": b.numero_boleto,
                        "PNR": b.localizador_pnr,
                        "Pasajero": b.nombre_pasajero_procesado or b.nombre_pasajero_completo,
                        "Aerolínea": b.aerolinea_emisora,
                        "Monto Neto": float(b.tarifa_base or 0),
                        "Comisión": float(b.comision_agencia or 0),
                        "Total": float(b.total_boleto or 0),
                        "Estado": "Auditado" if b.venta_asociada else "Pendiente",
                    }
                )

            if detalles_full:
                pd.DataFrame(detalles_full).to_excel(
                    writer, sheet_name="Detalle Boletos", index=False
                )

        output.seek(0)
        return output

    @staticmethod
    def get_stats_graficas_boletos(agencia, fecha_inicio=None, fecha_fin=None):
        """
        Retorna datos estructurados para visualización en gráficas.
        """
        from django.apps import apps

        BoletoImportado = apps.get_model("bookings", "BoletoImportado")
        qs = BoletoImportado.objects.filter(agencia=agencia, estado_parseo="COM")

        if fecha_inicio:
            qs = qs.filter(fecha_emision_boleto__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_emision_boleto__lte=fecha_fin)

        # 1. Top 5 Aerolíneas (Pie/Doughnut Chart)
        top_aero = (
            qs.values("aerolinea_emisora")
            .annotate(total=Sum("total_boleto"))
            .order_by("-total")[:5]
        )

        labels_aero = [item["aerolinea_emisora"] or "Desconocida" for item in top_aero]
        data_aero = [float(item["total"] or 0) for item in top_aero]

        # 2. Evolución Mensual de Comisiones (Line/Bar Chart)
        # Procesamos en Python para evitar problemas con TruncMonth en PostgreSQL
        from collections import OrderedDict

        mensual = OrderedDict()

        boletos = qs.filter(fecha_emision_boleto__isnull=False).values(
            "fecha_emision_boleto", "comision_agencia", "total_boleto"
        )

        for b in boletos:
            fecha = b.get("fecha_emision_boleto")
            if fecha is None:
                continue
            key = fecha.strftime("%b %Y")
            if key not in mensual:
                mensual[key] = {"comisiones": 0.0, "ventas": 0.0}
            mensual[key]["comisiones"] += float(b.get("comision_agencia") or 0)
            mensual[key]["ventas"] += float(b.get("total_boleto") or 0)

        labels_evolucion = list(mensual.keys())
        data_comisiones = [m["comisiones"] for m in mensual.values()]
        data_ventas = [m["ventas"] for m in mensual.values()]

        return {
            "aerolineas": {"labels": labels_aero, "data": data_aero},
            "evolucion": {
                "labels": labels_evolucion,
                "comisiones": data_comisiones,
                "ventas": data_ventas,
            },
        }

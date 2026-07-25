"""Servicio de report exporter para la aplicación reports.
"""

import csv
import io
import logging

logger = logging.getLogger(__name__)


def exportar_csv(kpi_metrics):
    """Exporta el resumen KPI a CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Métrica", "Valor"])
    r = kpi_metrics.resumen()
    for key, val in r.items():
        writer.writerow([key.replace("_", " ").title(), val])

    writer.writerow([])
    writer.writerow(["Ventas por Día (últimos 30)"])
    writer.writerow(["Fecha", "Ventas"])
    for fecha, count in kpi_metrics.ventas_por_dia(30).items():
        writer.writerow([fecha, count])

    writer.writerow([])
    writer.writerow(["Ventas por Vendedor"])
    writer.writerow(["Vendedor", "Ventas", "Monto"])
    for r in kpi_metrics.ventas_por_vendedor():
        writer.writerow([r["creado_por__email"], r["total"], r["monto"]])

    return output.getvalue()

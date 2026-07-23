"""Prepara datos en formato Chart.js para los gráficos del dashboard KPI."""


def ventas_diarias_chart(kpi_metrics):
    """Gráfico de línea: ventas por día (últimos 30 días)."""
    data = kpi_metrics.ventas_por_dia(30)
    return {
        "type": "line",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{
                "label": "Ventas",
                "data": list(data.values()),
                "borderColor": "#3B82F6",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "fill": True,
                "tension": 0.3,
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "x": {"ticks": {"maxTicksLimit": 10, "color": "#6B7280"}, "grid": {"display": False}},
                "y": {"ticks": {"color": "#6B7280"}, "grid": {"color": "rgba(107, 114, 128, 0.1)"}},
            },
        },
    }


def ventas_por_vendedor_chart(kpi_metrics):
    """Gráfico de barras: ventas por vendedor."""
    data = kpi_metrics.ventas_por_vendedor()
    labels = [r["creado_por__email"].split("@")[0] for r in data]
    valores = [r["total"] for r in data]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Ventas",
                "data": valores,
                "backgroundColor": ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"],
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "x": {"ticks": {"color": "#6B7280"}, "grid": {"display": False}},
                "y": {"ticks": {"color": "#6B7280"}, "grid": {"color": "rgba(107, 114, 128, 0.1)"}},
            },
        },
    }


def boletos_por_aerolinea_chart(kpi_metrics):
    """Gráfico de pastel: boletos por aerolínea."""
    data = kpi_metrics.boletos_por_aerolinea()
    labels = list(data.keys())
    valores = list(data.values())
    colores = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4"]
    return {
        "type": "doughnut",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": valores,
                "backgroundColor": colores[:len(valores)],
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"position": "right", "labels": {"color": "#D1D5DB", "boxWidth": 12}},
            },
        },
    }


def resumen_cards(kpi_metrics):
    """Cards de resumen para el dashboard."""
    r = kpi_metrics.resumen()
    return [
        {"titulo": "Ventas Totales", "valor": r["total_ventas"], "icono": "receipt", "color": "primary"},
        {"titulo": "Monto Total", "valor": f"${r['monto_total']:,.2f}", "icono": "payments", "color": "emerald"},
        {"titulo": "Utilidad", "valor": f"${r['utilidad']:,.2f}", "icono": "trending_up", "color": "emerald"},
        {"titulo": "Margen Bruto", "valor": f"{r['margen_bruto']:.1f}%", "icono": "pie_chart", "color": "amber"},
        {"titulo": "Ticket Promedio", "valor": f"${r['ticket_promedio']:,.2f}", "icono": "confirmation_number", "color": "primary"},
        {"titulo": "Clientes", "valor": r["clientes"], "icono": "people", "color": "purple"},
        {"titulo": "Boletos", "valor": r["boletos"], "icono": "flight", "color": "cyan"},
        {"titulo": "Comisiones Pend.", "valor": r["comisiones_pendientes"], "icono": "pending_actions", "color": "amber"},
    ]

from django.db.models import Q
from core.models.ventas import Venta

class ReportDataAggregator:
    """
    Service to fetch and aggregate data for reports.
    """

    @staticmethod
    def get_general_sales_data(start_date=None, end_date=None):
        """
        Fetches general sales data filtered by date range.
        Returns a tuple: (headers, data_rows)
        """
        queryset = Venta.objects.select_related('cliente', 'moneda', 'agencia').all()

        if start_date:
            queryset = queryset.filter(fecha_venta__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(fecha_venta__date__lte=end_date)
            
        # Headers for the Excel file
        headers = [
            "ID Venta",
            "Localizador",
            "Fecha",
            "Cliente",
            "Documento Cliente",
            "Total",
            "Moneda",
            "Estado",
            "Agencia"
        ]

        data = []
        for venta in queryset:
            cliente_nombre = str(venta.cliente) if venta.cliente else "N/A"
            cliente_documento = venta.cliente.numero_pasaporte if venta.cliente else ""
            
            row = [
                venta.id_venta,
                venta.localizador,
                venta.fecha_venta.replace(tzinfo=None) if venta.fecha_venta else None, # Remove TZ for Excel
                cliente_nombre,
                cliente_documento,
                venta.total_venta,
                str(venta.moneda) if venta.moneda else "",
                venta.get_estado_display(),
                str(venta.agencia) if venta.agencia else ""
            ]
            data.append(row)

        return headers, data

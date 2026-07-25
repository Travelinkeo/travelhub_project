"""Migración de base de datos para reports.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    initial = True

    dependencies = [
        ("core", "0056_agenciasetupprogress"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReporteKPI",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120)),
                ("tipo", models.CharField(choices=[("ventas", "Ventas"), ("rentabilidad", "Rentabilidad"), ("tickets", "Tickets/Boletos"), ("clientes", "Clientes"), ("comisiones", "Comisiones"), ("general", "General")], default="general", max_length=30)),
                ("periodo", models.CharField(choices=[("diario", "Diario"), ("semanal", "Semanal"), ("mensual", "Mensual"), ("trimestral", "Trimestral"), ("anual", "Anual")], default="mensual", max_length=30)),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("agencia", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_items", to="core.agencia")),
            ],
            options={"verbose_name": "Reporte KPI", "verbose_name_plural": "Reportes KPI"},
        ),
        migrations.CreateModel(
            name="KpiSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("metrica", models.CharField(choices=[("ventas_totales", "Ventas Totales"), ("ventas_mensuales", "Ventas Mensuales"), ("ventas_diarias", "Ventas Diarias"), ("promedio_venta", "Ticket Promedio"), ("margen_bruto", "Margen Bruto %"), ("utilidad_total", "Utilidad Total"), ("boletos_importados", "Boletos Importados"), ("tasa_exito_importacion", "Tasa de Éxito Importación"), ("clientes_nuevos", "Clientes Nuevos"), ("clientes_totales", "Clientes Totales"), ("comisiones_pendientes", "Comisiones Pendientes"), ("comisiones_liquidadas", "Comisiones Liquidadas")], max_length=40)),
                ("valor", models.DecimalField(decimal_places=2, max_digits=14)),
                ("fecha", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("agencia", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_items", to="core.agencia")),
            ],
            options={
                "verbose_name": "Snapshot KPI",
                "verbose_name_plural": "Snapshots KPI",
                "ordering": ["-fecha"],
                "unique_together": {("agencia", "metrica", "fecha")},
            },
        ),
        migrations.CreateModel(
            name="ReporteProgramado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120)),
                ("tipo", models.CharField(choices=[("ventas", "Ventas"), ("rentabilidad", "Rentabilidad"), ("tickets", "Tickets/Boletos"), ("clientes", "Clientes"), ("comisiones", "Comisiones"), ("general", "General")], default="general", max_length=30)),
                ("frecuencia", models.CharField(choices=[("diario", "Diario"), ("semanal", "Semanal"), ("mensual", "Mensual"), ("trimestral", "Trimestral"), ("anual", "Anual")], default="semanal", max_length=20)),
                ("dia_semana", models.IntegerField(blank=True, choices=[(1, "Lunes"), (2, "Martes"), (3, "Miércoles"), (4, "Jueves"), (5, "Viernes"), (6, "Sábado"), (7, "Domingo")], help_text="Para frecuencia semanal", null=True)),
                ("activo", models.BooleanField(default=True)),
                ("destinatarios", models.JSONField(default=list, help_text="Lista de emails")),
                ("ultimo_envio", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("agencia", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_items", to="core.agencia")),
            ],
            options={
                "verbose_name": "Reporte Programado",
                "verbose_name_plural": "Reportes Programados",
            },
        ),
    ]

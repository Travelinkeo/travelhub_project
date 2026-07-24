import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("contabilidad", "0012_asientocontable_estado_asientocontable_tipo_asiento"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReporteVentaProveedor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("proveedor_nombre", models.CharField(db_index=True, max_length=100)),
                (
                    "codigo_agencia_proveedor",
                    models.CharField(blank=True, default="", max_length=50),
                ),
                ("asunto_correo", models.CharField(blank=True, default="", max_length=255)),
                ("emisor_correo", models.CharField(blank=True, default="", max_length=150)),
                ("fecha_reporte_desde", models.DateField(blank=True, null=True)),
                ("fecha_reporte_hasta", models.DateField(blank=True, null=True)),
                ("fecha_procesamiento", models.DateTimeField(auto_now_add=True)),
                (
                    "nombre_archivo_adjunto",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "saldo_anterior",
                    models.DecimalField(decimal_places=2, default=0, max_digits=15),
                ),
                (
                    "monto_total_ventas",
                    models.DecimalField(decimal_places=2, default=0, max_digits=15),
                ),
                (
                    "saldo_final",
                    models.DecimalField(decimal_places=2, default=0, max_digits=15),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PROCESADO", "Procesado"),
                            ("CONCILIADO", "Conciliado"),
                            ("DIFERENCIA", "Con Diferencias"),
                            ("ERROR", "Error"),
                        ],
                        default="PROCESADO",
                        max_length=25,
                    ),
                ),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "agencia",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)s_agencia",
                        to="core.agencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reporte de Venta de Proveedor",
                "verbose_name_plural": "Reportes de Ventas de Proveedores",
                "ordering": ["-fecha_procesamiento"],
            },
        ),
        migrations.CreateModel(
            name="ItemReporteVentaProveedor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("fecha_emision", models.DateField(blank=True, null=True)),
                ("numero_factura", models.CharField(blank=True, default="", max_length=50)),
                ("numero_boleto", models.CharField(db_index=True, max_length=50)),
                ("pasajero", models.CharField(blank=True, default="", max_length=150)),
                ("aerolinea", models.CharField(blank=True, default="", max_length=100)),
                ("fecha_vuelo", models.DateField(blank=True, null=True)),
                ("ruta_itinerario", models.CharField(blank=True, default="", max_length=100)),
                ("monto_fare", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("monto_tax", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("monto_subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("monto_fee", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                (
                    "porcentaje_comision",
                    models.DecimalField(decimal_places=2, default=0, max_digits=5),
                ),
                ("monto_comision", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                (
                    "monto_neto_pagar",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                ("remarks", models.CharField(blank=True, default="", max_length=255)),
                (
                    "agencia",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)s_agencia",
                        to="core.agencia",
                    ),
                ),
                (
                    "reporte",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="contabilidad.reporteventaproveedor",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item de Reporte de Proveedor",
                "verbose_name_plural": "Items de Reportes de Proveedores",
                "ordering": ["reporte", "pk"],
            },
        ),
    ]

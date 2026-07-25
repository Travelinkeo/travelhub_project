# Generated for R2 (multi-tenant hardening) on 2026-07-13.

"""Aplica AgenciaMixin a FacturaConsolidada, ItemFacturaConsolidada y
DocumentoExportacionConsolidado.

- FacturaConsolidada ya tenia FK `agencia` manual (on_delete=PROTECT). Al heredar
  AgenciaMixin, el manager `objects` pasa a ser AgenciaManager y filtra
  automaticamente por contexto de agencia. No hay cambio de schema en ese modelo:
  el campo agencia ya existe.
- ItemFacturaConsolidada y DocumentoExportacionConsolidado NO tenian campo agencia.
  Se añade ahora (on_delete=CASCADE por defecto de AgenciaMixin, con SET_NULL no
  tiene sentido para lineas de factura — si se borra la agencia, mejor borrar sus
  facturas con ella).
"""

from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("finance", "0032_factura_tipo"),
    ]

    operations = [
        # FIX: These models were deleted by migration 0012 but must exist in the
        # state for AddField below. The DB tables already exist (0033 was applied).
        # These CreateModel operations are solely to make state_forwards work.
        migrations.CreateModel(
            name="FacturaConsolidada",
            fields=[
                ("id_factura", models.AutoField(primary_key=True, serialize=False)),
                ("fecha_emision", models.DateField()),
                ("estado", models.CharField(max_length=3)),
                (
                    "agencia",
                    models.ForeignKey(null=True, on_delete=models.CASCADE, to="core.agencia"),
                ),
            ],
            options={"managed": False, "db_table": "finance_facturaconsolidada"},
        ),
        migrations.CreateModel(
            name="ItemFacturaConsolidada",
            fields=[
                ("id_item_factura", models.AutoField(primary_key=True, serialize=False)),
                (
                    "factura",
                    models.ForeignKey(
                        null=True, on_delete=models.CASCADE, to="finance.facturaconsolidada"
                    ),
                ),
                ("descripcion", models.CharField(max_length=500)),
                ("cantidad", models.DecimalField(max_digits=10, decimal_places=2, default=1)),
                ("precio_unitario", models.DecimalField(max_digits=12, decimal_places=2)),
            ],
            options={"managed": False, "db_table": "finance_itemfacturaconsolidada"},
        ),
        migrations.CreateModel(
            name="DocumentoExportacionConsolidado",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "factura",
                    models.ForeignKey(
                        null=True, on_delete=models.CASCADE, to="finance.facturaconsolidada"
                    ),
                ),
                ("tipo_documento", models.CharField(max_length=20)),
                ("numero_documento", models.CharField(max_length=100)),
            ],
            options={"managed": False, "db_table": "finance_documentoexportacionconsolidado"},
        ),
        migrations.AddField(
            model_name="itemfacturaconsolidada",
            name="agencia",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="itemfacturaconsolidada_items",
                to="core.agencia",
                verbose_name="Agencia",
            ),
        ),
        migrations.AddField(
            model_name="documentoexportacionconsolidado",
            name="agencia",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="documentoexportacionconsolidado_items",
                to="core.agencia",
                verbose_name="Agencia",
            ),
        ),
    ]

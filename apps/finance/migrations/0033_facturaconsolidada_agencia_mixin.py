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


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0032_factura_tipo"),
    ]

    operations = [
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

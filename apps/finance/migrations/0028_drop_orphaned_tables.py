from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0027_remove_factura_finance_fac_venta_a_295412_idx_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DROP TABLE IF EXISTS bookings_facturaconsolidada CASCADE;
            DROP TABLE IF EXISTS bookings_itemfacturaconsolidada CASCADE;
            DROP TABLE IF EXISTS core_documentoexportacionconsolidado CASCADE;
            DROP TABLE IF EXISTS core_retencionislr CASCADE;
            """,
            reverse_sql="",
        )
    ]

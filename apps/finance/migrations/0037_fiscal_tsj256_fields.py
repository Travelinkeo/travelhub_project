# Generated migration for TSJ 00256, INATUR & LOCTEM fields in Factura model

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0036_gastooperativo_facturaconsolidada_retencionislr_reales"),
    ]

    operations = [
        migrations.AddField(
            model_name="factura",
            name="base_impuesto_municipal_usd",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Base imponible municipal LOCTEM (margen bruto real)",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="base_impuesto_municipal_ves",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Base imponible municipal en VES",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="ingreso_propio_agencia_usd",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Ingreso propio real por intermediación/comisión/fee",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="ingreso_propio_agencia_ves",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Ingreso propio real en VES a la tasa BCV",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="monto_cuenta_terceros_usd",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Monto pasante por cuenta de terceros (Boleto/Pasaje) - TSJ 00256",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="monto_cuenta_terceros_ves",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Monto pasante en VES a la tasa BCV",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="monto_impuesto_municipal_usd",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Impuesto municipal estimado (hasta 3% LOCTEM)",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="monto_impuesto_municipal_ves",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Impuesto municipal estimado en VES",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="monto_inatur_1_usd",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Aporte 1% INATUR sobre ingreso propio (Art. 13 Num. 6 Ley Turismo)",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="factura",
            name="monto_inatur_1_ves",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0"),
                help_text="Aporte 1% INATUR en VES a la tasa BCV",
                max_digits=15,
            ),
        ),
    ]

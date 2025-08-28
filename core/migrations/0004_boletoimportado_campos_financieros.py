# Generated manually - add financial fields to BoletoImportado
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_remove_factura_venta_asociada_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='boletoimportado',
            name='exchange_monto',
            field=models.DecimalField(verbose_name='Exchange', max_digits=10, decimal_places=2, blank=True, null=True, help_text='Monto de exchange o diferencial de cambio asociado al boleto.'),
        ),
        migrations.AddField(
            model_name='boletoimportado',
            name='void_monto',
            field=models.DecimalField(verbose_name='Void / Penalidad', max_digits=10, decimal_places=2, blank=True, null=True, help_text='Monto asociado a VOID (penalidad / reembolso negativo).'),
        ),
        migrations.AddField(
            model_name='boletoimportado',
            name='fee_servicio',
            field=models.DecimalField(verbose_name='Fee de Servicio', max_digits=10, decimal_places=2, blank=True, null=True, help_text='Fee cobrado por la agencia por gestión del boleto.'),
        ),
        migrations.AddField(
            model_name='boletoimportado',
            name='igtf_monto',
            field=models.DecimalField(verbose_name='IGTF', max_digits=10, decimal_places=2, blank=True, null=True, help_text='Impuesto a las Grandes Transacciones Financieras u otras retenciones locales.'),
        ),
        migrations.AddField(
            model_name='boletoimportado',
            name='comision_agencia',
            field=models.DecimalField(verbose_name='Comisión Agencia', max_digits=10, decimal_places=2, blank=True, null=True, help_text='Comisión propia de la agencia respecto al boleto.'),
        ),
    ]

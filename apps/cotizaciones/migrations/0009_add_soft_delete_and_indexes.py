# Generated manually — adds SoftDeleteModel fields + missing indexes

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("cotizaciones", "0008_alter_cotizacion_table_alter_itemcotizacion_table"),
    ]

    operations = [
        # -- Cotizacion soft delete fields --
        migrations.AddField(
            model_name="cotizacion",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="cotizacion",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        # -- ItemCotizacion soft delete fields --
        migrations.AddField(
            model_name="itemcotizacion",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="itemcotizacion",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        # -- Missing indexes on Cotizacion --
        migrations.AlterField(
            model_name="cotizacion",
            name="estado",
            field=models.CharField(
                choices=[
                    ("BOR", "Borrador"),
                    ("ENV", "Enviada al Cliente"),
                    ("VIS", "Vista por Cliente"),
                    ("ACE", "Aceptada"),
                    ("REC", "Rechazada"),
                    ("VEN", "Vencida"),
                    ("CON", "Convertida a Venta"),
                ],
                db_index=True,
                default="BOR",
                max_length=3,
                verbose_name="Estado",
            ),
        ),
        migrations.AlterField(
            model_name="cotizacion",
            name="fecha_emision",
            field=models.DateField(
                db_index=True, default=timezone.now, verbose_name="Fecha de Emisi\xf3n"
            ),
        ),
        # -- Composite indexes --
        migrations.AddIndex(
            model_name="cotizacion",
            index=models.Index(fields=["agencia", "estado"], name="idx_cotizacion_agencia_estado"),
        ),
        migrations.AddIndex(
            model_name="cotizacion",
            index=models.Index(
                fields=["agencia", "fecha_emision"], name="idx_cotizacion_agencia_fecha_emision"
            ),
        ),
    ]

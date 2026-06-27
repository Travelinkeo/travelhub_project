from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0025_add_ocr_fields_pasajero"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pasajero",
            name="apellidos_ocr",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="pasajero",
            name="nombres_ocr",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="pasajero",
            name="genero",
            field=models.CharField(
                blank=True,
                choices=[("M", "Masculino"), ("F", "Femenino"), ("X", "Otro")],
                max_length=1,
                null=True,
            ),
        ),
    ]

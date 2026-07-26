from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0027_mensajewhatsapp_es_bot_alter_cliente_foto_perfil_and_more"),
        ("bookings", "0037_tarifarioproveedor_add_agencia_proveedor"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="es_proveedor",
            field=models.BooleanField(
                default=False,
                help_text="Marcar si este cliente también provee servicios (ej: aerolínea, hotel, consolidador).",
                verbose_name="También es Proveedor",
            ),
        ),
        migrations.AddField(
            model_name="cliente",
            name="proveedor_vinculado",
            field=models.ForeignKey(
                blank=True,
                help_text="Registro de proveedor asociado a este cliente.",
                null=True,
                on_delete=models.SET_NULL,
                related_name="clientes_asociados",
                to="bookings.proveedor",
                verbose_name="Proveedor Vinculado",
            ),
        ),
    ]

# Generated for R1 hardening (CASCADE → SET_NULL) on 2026-07-13.

"""Cambiar on_delete=CASCADE a on_delete=SET_NULL en FKs de CRM que apuntan
a Cliente, User, Venta, FreelancerProfile.

Razon: preservar históricos al borrar físicamente entidades referenciadas.
- Borrar un Cliente ya no borra sus leads, mensajes WhatsApp, mensajes
  programados o pasaportes escaneados — quedan huérfanos para auditoría.
- Borrar un User ya no borra su perfil Freelancer — mantiene comisiones.
- Borrar una Venta o un FreelancerProfile ya no borra las ComisionFreelancer
  asociadas — mantiene histórico de pagos de comisiones.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0032_cliente_telegram_chat_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="oportunidadviaje",
            name="cliente",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="oportunidades",
                to="crm.cliente",
            ),
        ),
        migrations.AlterField(
            model_name="freelancerprofile",
            name="usuario",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="perfil_freelancer",
                to="auth.User",
            ),
        ),
        migrations.AlterField(
            model_name="comisionfreelancer",
            name="venta",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="comision_asignada",
                to="bookings.venta",
            ),
        ),
        migrations.AlterField(
            model_name="comisionfreelancer",
            name="freelancer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="comisiones_generadas",
                to="crm.freelancerprofile",
            ),
        ),
        migrations.AlterField(
            model_name="mensajewhatsapp",
            name="cliente",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="mensajes_whatsapp",
                to="crm.cliente",
            ),
        ),
        migrations.AlterField(
            model_name="whatsappscheduledmessage",
            name="cliente",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="whatsapp_programados",
                to="crm.cliente",
            ),
        ),
        migrations.AlterField(
            model_name="pasaporteescaneado",
            name="cliente",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                to="crm.cliente",
            ),
        ),
    ]

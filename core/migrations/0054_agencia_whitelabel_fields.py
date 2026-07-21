from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0053_ssoprovider.py"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenciaconfiguracion",
            name="csp_directives",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Directivas CSP adicionales específicas de la agencia. "
                "Ej: {'script-src': ['https://miwidget.com'], 'img-src': ['https://imagenes.miagencia.com']}",
            ),
        ),
        migrations.AddField(
            model_name="agenciabranding",
            name="template_pack",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Sobre-escribe templates globales con una carpeta 'templates/{template_pack}/' específica de la agencia. "
                "Ej: 'agencia_1' busca en core/templates/agencia_1/ antes de fallback a global.",
                max_length=50,
            ),
        ),
    ]

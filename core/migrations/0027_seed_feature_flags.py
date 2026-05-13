# Generated - Data migration: seeds default FeatureFlags

from django.db import migrations

DEFAULT_FLAGS = [
    {"nombre": "whatsapp_automation", "enabled": True, "description": "Notificaciones automaticas por WhatsApp"},
    {"nombre": "ai_parser_v2", "enabled": True, "description": "Parser universal con Gemini (v2)"},
    {"nombre": "email_monitor", "enabled": True, "description": "Monitoreo IMAP de correos de boletos"},
    {"nombre": "marketing_ai", "enabled": True, "description": "Generacion IA de contenido marketing"},
    {"nombre": "magic_quoter", "enabled": True, "description": "Cotizador magico con IA (GDS→Cotizacion)"},
    {"nombre": "migration_checker", "enabled": True, "description": "Verificacion de requisitos migratorios"},
    {"nombre": "hotel_engine", "enabled": True, "description": "Motor de busqueda y cotizacion de hoteles"},
    {"nombre": "beta_features", "enabled": False, "description": "Funcionalidades experimentales"},
]


def seed_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("core", "FeatureFlag")
    for flag_data in DEFAULT_FLAGS:
        FeatureFlag.objects.get_or_create(
            nombre=flag_data["nombre"],
            agencia=None,
            defaults={
                "enabled": flag_data["enabled"],
                "description": flag_data["description"],
                "rollout_percentage": 100,
            },
        )


def remove_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("core", "FeatureFlag")
    names = [f["nombre"] for f in DEFAULT_FLAGS]
    FeatureFlag.objects.filter(nombre__in=names, agencia=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_featureflag"),
    ]

    operations = [
        migrations.RunPython(seed_feature_flags, remove_feature_flags),
    ]

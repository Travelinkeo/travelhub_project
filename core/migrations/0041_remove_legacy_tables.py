from django.db import migrations


class Migration:
    """Migración de base de datos generada por Django."""
    dependencies = [
        ("core", "0040_aeropuerto"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DROP TABLE IF EXISTS core_productoterrestre CASCADE;
            DROP TABLE IF EXISTS core_tarifarioproveedor CASCADE;
            DROP TABLE IF EXISTS core_comisionoverrideaerolinea CASCADE;
            DROP TABLE IF EXISTS core_hoteltarifario CASCADE;
            DROP TABLE IF EXISTS core_imagenhotel CASCADE;
            DROP TABLE IF EXISTS core_tipohabitacion CASCADE;
            DROP TABLE IF EXISTS core_tarifahabitacion CASCADE;
            DROP TABLE IF EXISTS core_asientocontable CASCADE;
            DROP TABLE IF EXISTS core_plancontable CASCADE;
            DROP TABLE IF EXISTS core_detalleasiento CASCADE;
            DROP TABLE IF EXISTS core_liquidacionproveedor CASCADE;
            DROP TABLE IF EXISTS core_itemliquidacion CASCADE;
            """,
            reverse_sql="",
        ),
    ]

"""Migración de base de datos para bookings.
"""

from django.db import connection, migrations

_TABLE_RENAMES = [
    ("core_actividadservicio", "bookings_actividadservicio"),
    ("core_alojamientoreserva", "bookings_alojamientoreserva"),
    ("core_alquilerautoreserva", "bookings_alquilerautoreserva"),
    ("core_boletoimportado", "bookings_boletoimportado"),
    ("core_circuitodia", "bookings_circuitodia"),
    ("core_circuitoturistico", "bookings_circuitoturistico"),
    ("core_comisionproveedorservicio", "bookings_comisionproveedorservicio"),
    ("core_cruceroreserva", "bookings_cruceroreserva"),
    ("core_eventoservicio", "bookings_eventoservicio"),
    ("core_feeventa", "bookings_feeventa"),
    ("core_itemventa", "bookings_itemventa"),
    ("core_pagoventa", "bookings_pagoventa"),
    ("core_paqueteaereo", "bookings_paqueteaereo"),
    ("core_productoservicio", "bookings_productoservicio"),
    ("core_proveedor", "bookings_proveedor"),
    ("core_segmentovuelo", "bookings_segmentovuelo"),
    ("core_servicioadicionaldetalle", "bookings_servicioadicionaldetalle"),
    ("core_solicitudanulacion", "bookings_solicitudanulacion"),
    ("core_trasladoservicio", "bookings_trasladoservicio"),
    ("core_ventaparsemetadata", "bookings_ventaparsemetadata"),
    ("core_venta_pasajeros", "bookings_venta_pasajeros"),
    ("core_venta", "bookings_venta"),
]


_BOOKINGS_TABLES = [
    "bookings_actividadservicio",
    "bookings_alojamientoreserva",
    "bookings_alquilerautoreserva",
    "bookings_amenity",
    "bookings_boletoimportado",
    "bookings_boletoimportadotransito",
    "bookings_circuitodia",
    "bookings_circuitoturistico",
    "bookings_comisionoverrideaerolinea",
    "bookings_comisionproveedorservicio",
    "bookings_cruceroreserva",
    "bookings_eventoservicio",
    "bookings_feeventa",
    "bookings_hoteltarifario",
    "bookings_imagenhotel",
    "bookings_itemventa",
    "bookings_pagoventa",
    "bookings_paqueteaereo",
    "bookings_productoservicio",
    "bookings_productoterrestre",
    "bookings_proveedor",
    "bookings_segmentovuelo",
    "bookings_servicioadicionaldetalle",
    "bookings_solicitudanulacion",
    "bookings_tarifahabitacion",
    "bookings_tarifarioproveedor",
    "bookings_tipohabitacion",
    "bookings_trasladoservicio",
    "bookings_venta",
    "bookings_venta_pasajeros",
    "bookings_ventaauditfinding",
    "bookings_ventaparsemetadata",
]


def _rename_tables(apps, schema_editor):
    # _rename_tables:  rename tables. Args: según implementación. Returns: según implementación.
    with connection.cursor() as cursor:
        existing = _get_existing_tables(cursor)
        for old_name, new_name in _TABLE_RENAMES:
            if old_name in existing and new_name not in existing:
                cursor.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')


def _rename_indexes_and_constraints(apps, schema_editor):
    # _rename_indexes_and_constraints:  rename indexes and constraints. Args: según implementación. Returns: según implementación.
    with connection.cursor() as cursor:
        existing = _get_existing_tables(cursor)
        for table in _BOOKINGS_TABLES:
            if table not in existing:
                continue
            _rename_indexes_for(cursor, table)
            _rename_constraints_for(cursor, table)


def _get_existing_tables(cursor):
    # _get_existing_tables:  get existing tables. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    return {row[0] for row in cursor.fetchall()}


def _rename_indexes_for(cursor, table):
    # _rename_indexes_for:  rename indexes for. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT indexname FROM pg_indexes WHERE tablename = %s AND schemaname = 'public'",
        [table],
    )
    for (idx_name,) in cursor.fetchall():
        if idx_name.startswith("core_"):
            new_name = "bookings_" + idx_name[len("core_") :]
            if not _index_exists(cursor, new_name):
                cursor.execute(f'ALTER INDEX "{idx_name}" RENAME TO "{new_name}"')


def _rename_constraints_for(cursor, table):
    # _rename_constraints_for:  rename constraints for. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = %s::regclass AND connamespace = 'public'::regnamespace",
        [table],
    )
    for (con_name,) in cursor.fetchall():
        if con_name.startswith("core_"):
            new_name = "bookings_" + con_name[len("core_") :]
            if not _constraint_exists(cursor, new_name):
                cursor.execute(
                    f'ALTER TABLE "{table}" RENAME CONSTRAINT "{con_name}" TO "{new_name}"'
                )


def _index_exists(cursor, name):
    # _index_exists:  index exists. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname = %s AND schemaname = 'public'",
        [name],
    )
    return cursor.fetchone() is not None


def _constraint_exists(cursor, name):
    # _constraint_exists:  constraint exists. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = %s AND connamespace = 'public'::regnamespace",
        [name],
    )
    return cursor.fetchone() is not None


def _reverse_rename_tables(apps, schema_editor):
    # _reverse_rename_tables:  reverse rename tables. Args: según implementación. Returns: según implementación.
    with connection.cursor() as cursor:
        existing = _get_existing_tables(cursor)
        for old_name, new_name in reversed(_TABLE_RENAMES):
            if new_name in existing and old_name not in existing:
                cursor.execute(f'ALTER TABLE "{new_name}" RENAME TO "{old_name}"')


def _reverse_rename_indexes_and_constraints(apps, schema_editor):
    # _reverse_rename_indexes_and_constraints:  reverse rename indexes and constraints. Args: según implementación. Returns: según implementación.
    _rename_indexes_and_constraints(apps, schema_editor)


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("bookings", "0035_alter_feeventa_venta_alter_pagoventa_venta"),
    ]

    operations = [
        migrations.RunPython(
            _rename_tables,
            _reverse_rename_tables,
        ),
        migrations.RunPython(
            _rename_indexes_and_constraints,
            _reverse_rename_indexes_and_constraints,
        ),
    ]

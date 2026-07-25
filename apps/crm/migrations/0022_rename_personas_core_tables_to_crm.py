"""Migración de base de datos para crm.
"""

from django.db import connection, migrations

_TABLE_RENAMES = [
    ("personas_cliente", "crm_cliente"),
    ("personas_pasajero", "crm_pasajero"),
    ("personas_cliente_pasajeros", "crm_cliente_pasajeros"),
    ("core_pasaporte_escaneado", "crm_pasaporteescaneado"),
    ("crm_whatsapp_mensaje", "crm_mensajewhatsapp"),
]

_CRM_TABLES = [
    "crm_cliente",
    "crm_pasajero",
    "crm_cliente_pasajeros",
    "crm_pasaporteescaneado",
    "crm_mensajewhatsapp",
]

_INDEX_PREFIX_MAP = {
    "personas_": "crm_",
    "core_pasaporte_escaneado_": "crm_pasaporteescaneado_",
}

_CONSTRAINT_PREFIX_MAP = {
    "personas_": "crm_",
    "core_pasaporte_escan_": "crm_pasaporteescaneado_",
}

_FK_REFERENCES_REPLACE = [
    ("_fk_personas_", "_fk_crm_"),
]


def _get_existing_tables(cursor):
    # _get_existing_tables:  get existing tables. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    return {row[0] for row in cursor.fetchall()}


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


def _rename_indexes_for(cursor, table):
    # _rename_indexes_for:  rename indexes for. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT indexname FROM pg_indexes WHERE tablename = %s AND schemaname = 'public'",
        [table],
    )
    for (idx_name,) in cursor.fetchall():
        new_name = _apply_prefix_map(idx_name, _INDEX_PREFIX_MAP)
        if new_name != idx_name and not _index_exists(cursor, new_name):
            cursor.execute(f'ALTER INDEX "{idx_name}" RENAME TO "{new_name}"')


def _rename_constraints_for(cursor, table):
    # _rename_constraints_for:  rename constraints for. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = %s::regclass AND connamespace = 'public'::regnamespace",
        [table],
    )
    for (con_name,) in cursor.fetchall():
        new_name = _apply_prefix_map(con_name, _CONSTRAINT_PREFIX_MAP)
        if new_name != con_name and not _constraint_exists(cursor, new_name):
            cursor.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{con_name}" TO "{new_name}"')


def _rename_fk_references_on_other_tables(cursor):
    # _rename_fk_references_on_other_tables:  rename fk references on other tables. Args: según implementación. Returns: según implementación.
    cursor.execute(
        "SELECT conrelid::regclass::text AS from_table, conname "
        "FROM pg_constraint "
        "WHERE conname LIKE '%%_fk_personas_%%' "
        "AND connamespace = 'public'::regnamespace "
        "ORDER BY conname"
    )
    for from_table, con_name in cursor.fetchall():
        new_name = con_name.replace("_fk_personas_", "_fk_crm_")
        if not _constraint_exists(cursor, new_name):
            cursor.execute(
                f'ALTER TABLE "{from_table}" RENAME CONSTRAINT "{con_name}" TO "{new_name}"'
            )


def _apply_prefix_map(name, prefix_map):
    # _apply_prefix_map:  apply prefix map. Args: según implementación. Returns: según implementación.
    for old_prefix, new_prefix in prefix_map.items():
        if name.startswith(old_prefix):
            return new_prefix + name[len(old_prefix) :]
    return name


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
        for table in _CRM_TABLES:
            if table not in existing:
                continue
            _rename_indexes_for(cursor, table)
            _rename_constraints_for(cursor, table)
        _rename_fk_references_on_other_tables(cursor)


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
        ("crm", "0021_alter_cliente_table_alter_mensajewhatsapp_table_and_more"),
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

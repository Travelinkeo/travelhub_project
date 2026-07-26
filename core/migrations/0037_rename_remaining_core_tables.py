from django.db import connection, migrations

_TABLE_RENAMES = [
    ("core_aerolinea", "common_aerolinea"),
    ("core_ciudad", "common_ciudad"),
    ("core_pais", "common_pais"),
    ("core_factura", "finance_factura"),
    ("core_gastooperativo", "finance_gastooperativo"),
    ("core_itemfactura", "finance_itemfactura"),
    ("core_retencionislr", "finance_retencionislr"),
    ("core_tasacambio", "finance_tasacambio"),
    ("core_tipocambio", "finance_tipocambio"),
    ("core_asientocontable", "contabilidad_asientocontable"),
    ("core_detalleasiento", "contabilidad_detalleasiento"),
    ("core_plancontable", "contabilidad_plancontable"),
    ("core_liquidacionproveedor", "contabilidad_liquidacionproveedor"),
    ("core_itemliquidacion", "contabilidad_itemliquidacion"),
    ("core_cotizacion", "cotizaciones_cotizacion"),
    ("core_itemcotizacion", "cotizaciones_itemcotizacion"),
    ("core_comunicacionproveedor", "communications_comunicacionproveedor"),
    ("core_notificacionagente", "automation_notificacionagente"),
    ("core_notificacioninteligente", "automation_notificacioninteligente"),
]

_ORPHAN_TABLES = [
    "core_documentoexportacionconsolidado",
    "core_facturaconsolidada",
    "core_itemfacturaconsolidada",
]

_TABLE_PREFIX_MAP = {
    "core_aerolinea": "common_aerolinea",
    "core_ciudad": "common_ciudad",
    "core_pais": "common_pais",
    "core_factura": "finance_factura",
    "core_gastooperativo": "finance_gastooperativo",
    "core_itemfactura": "finance_itemfactura",
    "core_retencionislr": "finance_retencionislr",
    "core_tasacambio": "finance_tasacambio",
    "core_tipocambio": "finance_tipocambio",
    "core_asientocontable": "contabilidad_asientocontable",
    "core_detalleasiento": "contabilidad_detalleasiento",
    "core_plancontable": "contabilidad_plancontable",
    "core_liquidacionproveedor": "contabilidad_liquidacionproveedor",
    "core_itemliquidacion": "contabilidad_itemliquidacion",
    "core_cotizacion": "cotizaciones_cotizacion",
    "core_itemcotizacion": "cotizaciones_itemcotizacion",
    "core_comunicacionproveedor": "communications_comunicacionproveedor",
    "core_notificacionagente": "automation_notificacionagente",
    "core_notificacioninteligente": "automation_notificacioninteligente",
}

_APP_TABLES = list(_TABLE_PREFIX_MAP.values())


def _get_existing_tables(cursor):
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    return {row[0] for row in cursor.fetchall()}


def _index_exists(cursor, name):
    cursor.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname = %s AND schemaname = 'public'",
        [name],
    )
    return cursor.fetchone() is not None


def _constraint_exists(cursor, name):
    cursor.execute(
        "SELECT 1 FROM pg_constraint WHERE conname = %s AND connamespace = 'public'::regnamespace",
        [name],
    )
    return cursor.fetchone() is not None


def _rename_index(cursor, idx_name, new_name):
    if not _index_exists(cursor, new_name):
        cursor.execute(f'ALTER INDEX "{idx_name}" RENAME TO "{new_name}"')


def _rename_constraint(cursor, table, con_name, new_name):
    if not _constraint_exists(cursor, new_name):
        cursor.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{con_name}" TO "{new_name}"')


def _replace_core_prefix(name, new_table):
    for old_core, new_app in _TABLE_PREFIX_MAP.items():
        if name.startswith(old_core + "_"):
            return new_app + name[len(old_core) :]
    return name


def _rename_tables(apps, schema_editor):
    with connection.cursor() as cursor:
        existing = _get_existing_tables(cursor)
        for old_name, new_name in _TABLE_RENAMES:
            if old_name in existing and new_name not in existing:
                cursor.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
            elif old_name in existing and new_name in existing:
                cursor.execute(f'SELECT count(*) FROM "{old_name}"')
                (cnt,) = cursor.fetchone()
                if cnt == 0:
                    cursor.execute(f'DROP TABLE IF EXISTS "{old_name}" CASCADE')
        for orphan in _ORPHAN_TABLES:
            if orphan in existing:
                cursor.execute(f'DROP TABLE IF EXISTS "{orphan}" CASCADE')


def _rename_indexes_and_constraints(apps, schema_editor):
    with connection.cursor() as cursor:
        existing = _get_existing_tables(cursor)
        for table in _APP_TABLES:
            if table not in existing:
                continue
            new_prefix = table
            old_prefix = None
            for old_core, new_app in _TABLE_PREFIX_MAP.items():
                if new_app == table:
                    old_prefix = old_core
                    break
            if not old_prefix:
                continue
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE tablename = %s AND schemaname = 'public'",
                [table],
            )
            for (idx_name,) in cursor.fetchall():
                if idx_name.startswith(old_prefix + "_"):
                    new_name = new_prefix + idx_name[len(old_prefix) :]
                    _rename_index(cursor, idx_name, new_name)
            cursor.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = %s::regclass AND connamespace = 'public'::regnamespace",
                [table],
            )
            for (con_name,) in cursor.fetchall():
                if con_name.startswith(old_prefix + "_"):
                    new_name = new_prefix + con_name[len(old_prefix) :]
                    _rename_constraint(cursor, table, con_name, new_name)
        _rename_fk_references_on_other_tables(cursor)


def _rename_fk_references_on_other_tables(cursor):
    cursor.execute(
        "SELECT conrelid::regclass::text AS from_table, conname, "
        "confrelid::regclass::text AS to_table "
        "FROM pg_constraint "
        "WHERE contype = 'f' "
        "AND connamespace = 'public'::regnamespace "
        "AND conname LIKE '%%_fk_core_%%' "
        "ORDER BY conname"
    )
    rows = cursor.fetchall()
    for from_table, con_name, to_table in rows:
        new_app = _TABLE_PREFIX_MAP.get(to_table)
        if not new_app:
            continue
        suffix = con_name[con_name.find("_fk_core_") + len("_fk_core_") :]
        new_name = con_name[: con_name.find("_fk_core_")] + f"_fk_{new_app}_" + suffix
        if new_name != con_name and not _constraint_exists(cursor, new_name):
            cursor.execute(
                f'ALTER TABLE "{from_table}" RENAME CONSTRAINT "{con_name}" TO "{new_name}"'
            )


def _reverse_rename_tables(apps, schema_editor):
    with connection.cursor() as cursor:
        existing = _get_existing_tables(cursor)
        for old_name, new_name in reversed(_TABLE_RENAMES):
            if new_name in existing and old_name not in existing:
                cursor.execute(f'ALTER TABLE "{new_name}" RENAME TO "{old_name}"')


def _reverse_rename_indexes_and_constraints(apps, schema_editor):
    _rename_indexes_and_constraints(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_alter_agenciabranding_agencia_and_more"),
        ("bookings", "0036_rename_core_tables_to_bookings"),
        ("crm", "0022_rename_personas_core_tables_to_crm"),
        ("common", "0003_moneda"),
        ("communications", "0005_emailmonitorlog"),
        ("automation", "0005_alter_notificacionagente_agencia_and_more"),
        ("finance", "0022_remove_comisionventa_venta_remove_linkdepago_venta_and_more"),
        ("cotizaciones", "0007_alter_cotizacion_moneda"),
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

# Generated manually to fix missing columns from SeparateDatabaseAndState in migration 0009.
# Edited 2026-06-07: each ALTER is wrapped in a DO block that:
#   1. Locates the target table in either `core_` or `bookings_` namespace
#   2. Uses the correct PK column name (e.g. `id_proveedor`, `id_crucero`, `id_venta`)
#   3. Uses the correct FK target PK column
# This makes the migration safe in fresh DB (where tables are core_xxx) and in
# the dev/prod DB (where some bookings_xxx copies also exist).
from django.db import migrations


def _col(target_table_var, column, type_def, fk_table, fk_col):
    """
    Build a DO block that adds `column type_def` to the table referenced
    by target_table_var (which itself is set by a nested check).
    """
    return f"""
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'core_{target_table_var}') THEN
      EXECUTE 'ALTER TABLE core_{target_table_var} ADD COLUMN IF NOT EXISTS {column} {type_def}';
      EXECUTE 'ALTER TABLE core_{target_table_var} DROP CONSTRAINT IF EXISTS fk_{target_table_var}_{column}';
      EXECUTE 'ALTER TABLE core_{target_table_var} ADD CONSTRAINT fk_{target_table_var}_{column} FOREIGN KEY ({column}) REFERENCES {fk_table}({fk_col}) ON DELETE CASCADE';
    ELSIF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'bookings_{target_table_var}') THEN
      EXECUTE 'ALTER TABLE bookings_{target_table_var} ADD COLUMN IF NOT EXISTS {column} {type_def}';
      EXECUTE 'ALTER TABLE bookings_{target_table_var} DROP CONSTRAINT IF EXISTS fk_{target_table_var}_{column}';
      EXECUTE 'ALTER TABLE bookings_{target_table_var} ADD CONSTRAINT fk_{target_table_var}_{column} FOREIGN KEY ({column}) REFERENCES {fk_table}({fk_col}) ON DELETE CASCADE';
    END IF;
    """


def _col_setnull(target_table_var, column, type_def, fk_table, fk_col):
    """Same as _col but with ON DELETE SET NULL."""
    return f"""
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'core_{target_table_var}') THEN
      EXECUTE 'ALTER TABLE core_{target_table_var} ADD COLUMN IF NOT EXISTS {column} {type_def}';
      EXECUTE 'ALTER TABLE core_{target_table_var} DROP CONSTRAINT IF EXISTS fk_{target_table_var}_{column}';
      EXECUTE 'ALTER TABLE core_{target_table_var} ADD CONSTRAINT fk_{target_table_var}_{column} FOREIGN KEY ({column}) REFERENCES {fk_table}({fk_col}) ON DELETE SET NULL';
    ELSIF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'bookings_{target_table_var}') THEN
      EXECUTE 'ALTER TABLE bookings_{target_table_var} ADD COLUMN IF NOT EXISTS {column} {type_def}';
      EXECUTE 'ALTER TABLE bookings_{target_table_var} DROP CONSTRAINT IF EXISTS fk_{target_table_var}_{column}';
      EXECUTE 'ALTER TABLE bookings_{target_table_var} ADD CONSTRAINT fk_{target_table_var}_{column} FOREIGN KEY ({column}) REFERENCES {fk_table}({fk_col}) ON DELETE SET NULL';
    END IF;
    """


def _col_restrict(target_table_var, column, type_def, fk_table, fk_col):
    """Same as _col but with ON DELETE RESTRICT."""
    return f"""
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'core_{target_table_var}') THEN
      EXECUTE 'ALTER TABLE core_{target_table_var} ADD COLUMN IF NOT EXISTS {column} {type_def}';
      EXECUTE 'ALTER TABLE core_{target_table_var} DROP CONSTRAINT IF EXISTS fk_{target_table_var}_{column}';
      EXECUTE 'ALTER TABLE core_{target_table_var} ADD CONSTRAINT fk_{target_table_var}_{column} FOREIGN KEY ({column}) REFERENCES {fk_table}({fk_col}) ON DELETE RESTRICT';
    ELSIF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'bookings_{target_table_var}') THEN
      EXECUTE 'ALTER TABLE bookings_{target_table_var} ADD COLUMN IF NOT EXISTS {column} {type_def}';
      EXECUTE 'ALTER TABLE bookings_{target_table_var} DROP CONSTRAINT IF EXISTS fk_{target_table_var}_{column}';
      EXECUTE 'ALTER TABLE bookings_{target_table_var} ADD CONSTRAINT fk_{target_table_var}_{column} FOREIGN KEY ({column}) REFERENCES {fk_table}({fk_col}) ON DELETE RESTRICT';
    END IF;
    """


def _build_forward_sql():
    return [
        # 1. tarifarioproveedor: agencia_id (CASCADE) + proveedor_id (CASCADE)
        f"""DO $$ BEGIN {_col('tarifarioproveedor', 'agencia_id', 'bigint', 'core_agencia', 'id')} END $$;""",
        f"""DO $$ BEGIN {_col('tarifarioproveedor', 'proveedor_id', 'bigint', 'core_proveedor', 'id_proveedor')} END $$;""",
        # 2. hoteltarifario: agencia_id + tarifario_id
        f"""DO $$ BEGIN {_col('hoteltarifario', 'agencia_id', 'bigint', 'core_agencia', 'id')} END $$;""",
        f"""DO $$ BEGIN {_col('hoteltarifario', 'tarifario_id', 'bigint', 'core_tarifarioproveedor', 'id')} END $$;""",
        # 3. comisionoverrideaerolinea: aerolinea_id + tarifario_id
        f"""DO $$ BEGIN {_col('comisionoverrideaerolinea', 'aerolinea_id', 'bigint', 'core_aerolinea', 'id_aerolinea')} END $$;""",
        f"""DO $$ BEGIN {_col('comisionoverrideaerolinea', 'tarifario_id', 'bigint', 'core_tarifarioproveedor', 'id')} END $$;""",
        # 4. cruceroreserva: moneda_id (RESTRICT) + proveedor_id (SET NULL) + venta_id (CASCADE)
        f"""DO $$ BEGIN {_col_restrict('cruceroreserva', 'moneda_id', 'bigint', 'core_moneda', 'id_moneda')} END $$;""",
        f"""DO $$ BEGIN {_col_setnull('cruceroreserva', 'proveedor_id', 'bigint', 'core_proveedor', 'id_proveedor')} END $$;""",
        f"""DO $$ BEGIN {_col('cruceroreserva', 'venta_id', 'bigint', 'core_venta', 'id_venta')} END $$;""",
        # 5. imagenhotel: hotel_id
        f"""DO $$ BEGIN {_col('imagenhotel', 'hotel_id', 'bigint', 'core_hoteltarifario', 'id')} END $$;""",
        # 6. productoterrestre: agencia_id
        f"""DO $$ BEGIN {_col('productoterrestre', 'agencia_id', 'bigint', 'core_agencia', 'id')} END $$;""",
        # 7. tipohabitacion: hotel_id
        f"""DO $$ BEGIN {_col('tipohabitacion', 'hotel_id', 'bigint', 'core_hoteltarifario', 'id')} END $$;""",
        # 8. tarifahabitacion: tipo_habitacion_id
        f"""DO $$ BEGIN {_col('tarifahabitacion', 'tipo_habitacion_id', 'bigint', 'core_tipohabitacion', 'id')} END $$;""",
    ]


def _build_reverse_sql():
    bare_cols = [
        ("tarifarioproveedor", ["agencia_id", "proveedor_id"]),
        ("hoteltarifario", ["agencia_id", "tarifario_id"]),
        ("comisionoverrideaerolinea", ["aerolinea_id", "tarifario_id"]),
        ("cruceroreserva", ["moneda_id", "proveedor_id", "venta_id"]),
        ("imagenhotel", ["hotel_id"]),
        ("productoterrestre", ["agencia_id"]),
        ("tipohabitacion", ["hotel_id"]),
        ("tarifahabitacion", ["tipo_habitacion_id"]),
    ]
    sql = []
    for bare, cols in bare_cols:
        col_list = ",".join(cols)
        sql.append(f"""DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'core_{bare}') THEN
      EXECUTE 'ALTER TABLE core_{bare} DROP CONSTRAINT IF EXISTS fk_{bare}_' || split_part('{col_list}', ',', 1);
      EXECUTE 'ALTER TABLE core_{bare} DROP COLUMN IF EXISTS ' || '{col_list}';
    ELSIF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'bookings_{bare}') THEN
      EXECUTE 'ALTER TABLE bookings_{bare} DROP CONSTRAINT IF EXISTS fk_{bare}_' || split_part('{col_list}', ',', 1);
      EXECUTE 'ALTER TABLE bookings_{bare} DROP COLUMN IF EXISTS ' || '{col_list}';
    END IF;
END $$;""")
    return sql


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0029_venta_monto_neto_proveedor_venta_monto_venta_cliente_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_build_forward_sql(),
            reverse_sql=_build_reverse_sql(),
        ),
    ]

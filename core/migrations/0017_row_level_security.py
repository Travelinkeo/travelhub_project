from django.db import migrations

RLS_TABLES = [
    'core_venta',
    'core_itemventa',
    'core_boletoimportado',
    'core_pagoventa',
    'core_feeventa',
    'core_proveedor',
    'core_productoservicio',
    'core_comisionproveedorservicio',
    'core_alojamientoreserva',
    'core_trasladoservicio',
    'core_actividadservicio',
    'core_segmentovuelo',
    'core_alquilerautoreserva',
    'core_eventoservicio',
    'core_circuitoturistico',
    'core_paqueteaereo',
    'core_servicioadicionaldetalle',
    'core_factura',
    'core_gastooperativo',
    'crm_cliente',
    'crm_pasajero',
    'core_auditlog',
    'finance_reportereconciliacion',
    'finance_lineareportereconciliacion',
    'finance_conciliacionboleto',
    'finance_taxrefundopportunity',
    'finance_comisionventa',
    'finance_liquidacionagente',
    'marketing_campania',
]


def _build_forward_sql():
    sql = [
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'travelhub_app') "
        "THEN CREATE ROLE travelhub_app; END IF; END $$;",
    ]
    for t in RLS_TABLES:
        sql.append(
            f"DO $$ BEGIN "
            f"IF EXISTS (SELECT FROM pg_tables WHERE tablename = '{t.replace('core_', '')}' OR tablename = '{t}') "
            f"THEN ALTER TABLE {t} ENABLE ROW LEVEL SECURITY; "
            f"END IF; "
            f"END $$;"
        )
    for t in RLS_TABLES:
        sql.append(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {t};")
        sql.append(f"DROP POLICY IF EXISTS superadmin_bypass ON {t};")
    for t in RLS_TABLES:
        sql.append(
            f"DO $$ BEGIN "
            f"IF EXISTS (SELECT FROM pg_tables WHERE tablename = '{t.replace('core_', '')}' OR tablename = '{t}') "
            f"THEN "
            f"CREATE POLICY tenant_isolation_policy ON {t} "
            f"USING (agencia_id = current_setting('app.current_agencia_id', TRUE)::INTEGER); "
            f"END IF; "
            f"END $$;"
        )
    for t in RLS_TABLES:
        sql.append(
            f"DO $$ BEGIN "
            f"IF EXISTS (SELECT FROM pg_tables WHERE tablename = '{t.replace('core_', '')}' OR tablename = '{t}') "
            f"THEN "
            f"CREATE POLICY superadmin_bypass ON {t} "
            f"USING (current_setting('app.bypass_rls', TRUE) = 'true'); "
            f"END IF; "
            f"END $$;"
        )
    return sql


def _build_reverse_sql():
    sql = []
    for t in RLS_TABLES:
        sql.append(
            f"DO $$ BEGIN "
            f"IF EXISTS (SELECT FROM pg_tables WHERE tablename = '{t.replace('core_', '')}' OR tablename = '{t}') "
            f"THEN "
            f"DROP POLICY IF EXISTS tenant_isolation_policy ON {t}; "
            f"DROP POLICY IF EXISTS superadmin_bypass ON {t}; "
            f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY; "
            f"END IF; "
            f"END $$;"
        )
    return sql


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0016_add_critical_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql=_build_forward_sql(),
            reverse_sql=_build_reverse_sql(),
        ),
    ]
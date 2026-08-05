# Generated manually — reemplaza 0036 con CreateModel explícito para los 3 modelos
# que fueron managed=False y ahora son managed=True con tablas reales.

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0035_alter_canalrecaudacion_table_and_more"),
        ("common", "0001_initial"),
        ("crm", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── GastoOperativo ─────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS finance_gastooperativo (
                        id BIGSERIAL PRIMARY KEY,
                        descripcion VARCHAR(255) NOT NULL,
                        monto NUMERIC(12, 2) NOT NULL,
                        fecha DATE NOT NULL,
                        categoria VARCHAR(3) NOT NULL DEFAULT 'OTR',
                        notas TEXT NOT NULL DEFAULT '',
                        estado_contable VARCHAR(3) NOT NULL DEFAULT 'PEN',
                        error_contable_msg TEXT NULL,
                        tasa_bcv NUMERIC(12, 4) NULL,
                        comprobante VARCHAR(100) NULL,
                        creado TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                        actualizado TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                        agencia_id BIGINT NOT NULL REFERENCES core_agencia(id) ON DELETE CASCADE,
                        moneda_id BIGINT NOT NULL REFERENCES core_moneda(id_moneda) ON DELETE RESTRICT,
                        creado_por_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL
                    );
                    CREATE INDEX IF NOT EXISTS finance_gastooperativo_agencia_fecha
                        ON finance_gastooperativo (agencia_id, fecha);
                    CREATE INDEX IF NOT EXISTS finance_gastooperativo_agencia_categoria
                        ON finance_gastooperativo (agencia_id, categoria);
                    CREATE INDEX IF NOT EXISTS finance_gastooperativo_agencia_estado
                        ON finance_gastooperativo (agencia_id, estado_contable);
                    """,
                    reverse_sql="DROP TABLE IF EXISTS finance_gastooperativo;",
                ),
            ],
            state_operations=[
                migrations.AlterModelOptions(
                    name="gastooperativo",
                    options={
                        "ordering": ["-fecha", "-creado"],
                        "verbose_name": "Gasto Operativo",
                        "verbose_name_plural": "Gastos Operativos",
                    },
                ),
            ],
        ),
        # ── FacturaConsolidada ──────────────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS finance_facturaconsolidada (
                        id BIGSERIAL PRIMARY KEY,
                        numero_factura VARCHAR(50) NOT NULL UNIQUE,
                        numero_control VARCHAR(50) NOT NULL DEFAULT '',
                        fecha_emision DATE NOT NULL,
                        cliente_rif VARCHAR(20) NOT NULL DEFAULT '',
                        cliente_razon_social VARCHAR(200) NOT NULL DEFAULT '',
                        cliente_es_residente BOOLEAN NOT NULL DEFAULT TRUE,
                        tipo_operacion VARCHAR(2) NOT NULL DEFAULT 'VP',
                        subtotal_base_gravada NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        subtotal_exento NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        monto_iva_16 NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        monto_iva_adicional NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        monto_igtf NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        gran_total_usd NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        tasa_cambio_bcv NUMERIC(12, 4) NULL,
                        gran_total_ves NUMERIC(15, 2) NULL,
                        es_contribuyente_especial BOOLEAN NOT NULL DEFAULT FALSE,
                        estado VARCHAR(3) NOT NULL DEFAULT 'BOR',
                        archivo_pdf VARCHAR(100) NULL,
                        notas TEXT NOT NULL DEFAULT '',
                        creado TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                        actualizado TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                        agencia_id BIGINT NOT NULL REFERENCES core_agencia(id) ON DELETE CASCADE,
                        cliente_id BIGINT NULL REFERENCES crm_cliente(id_cliente) ON DELETE RESTRICT
                    );
                    CREATE INDEX IF NOT EXISTS finance_facturaconsolidada_agencia_estado
                        ON finance_facturaconsolidada (agencia_id, estado);
                    CREATE INDEX IF NOT EXISTS finance_facturaconsolidada_agencia_fecha
                        ON finance_facturaconsolidada (agencia_id, fecha_emision);
                    CREATE INDEX IF NOT EXISTS finance_facturaconsolidada_numero
                        ON finance_facturaconsolidada (numero_factura);
                    """,
                    reverse_sql="DROP TABLE IF EXISTS finance_facturaconsolidada;",
                ),
            ],
            state_operations=[
                migrations.AlterModelOptions(
                    name="facturaconsolidada",
                    options={
                        "ordering": ["-fecha_emision", "-creado"],
                        "verbose_name": "Factura Consolidada VEN-NIF",
                        "verbose_name_plural": "Facturas Consolidadas VEN-NIF",
                    },
                ),
            ],
        ),
        # ── ItemFacturaConsolidada ──────────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS finance_itemfacturaconsolidada (
                        id BIGSERIAL PRIMARY KEY,
                        descripcion VARCHAR(500) NOT NULL,
                        tipo_servicio VARCHAR(3) NOT NULL DEFAULT 'OTR',
                        cantidad NUMERIC(10, 2) NOT NULL DEFAULT 1.00,
                        precio_unitario NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        exento BOOLEAN NOT NULL DEFAULT FALSE,
                        alicuota_iva NUMERIC(5, 2) NOT NULL DEFAULT 16.00,
                        numero_boleto VARCHAR(50) NOT NULL DEFAULT '',
                        nombre_pasajero VARCHAR(200) NOT NULL DEFAULT '',
                        agencia_id BIGINT NOT NULL REFERENCES core_agencia(id) ON DELETE CASCADE,
                        factura_id BIGINT NOT NULL REFERENCES finance_facturaconsolidada(id) ON DELETE CASCADE
                    );
                    """,
                    reverse_sql="DROP TABLE IF EXISTS finance_itemfacturaconsolidada;",
                ),
            ],
            state_operations=[
                migrations.AlterModelOptions(
                    name="itemfacturaconsolidada",
                    options={
                        "verbose_name": "Ítem de Factura Consolidada",
                        "verbose_name_plural": "Ítems de Factura Consolidada",
                    },
                ),
            ],
        ),
        # ── RetencionISLR ───────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS finance_retencionislr (
                        id BIGSERIAL PRIMARY KEY,
                        numero_comprobante VARCHAR(50) NOT NULL UNIQUE,
                        fecha_emision DATE NOT NULL,
                        periodo_fiscal VARCHAR(7) NULL,
                        tipo_operacion VARCHAR(2) NOT NULL DEFAULT 'CM',
                        retenido_rif VARCHAR(20) NOT NULL DEFAULT '',
                        retenido_nombre VARCHAR(200) NOT NULL DEFAULT '',
                        base_imponible NUMERIC(12, 2) NOT NULL,
                        porcentaje_retencion NUMERIC(5, 2) NOT NULL DEFAULT 5.00,
                        monto_retenido NUMERIC(12, 2) NULL,
                        estado VARCHAR(3) NOT NULL DEFAULT 'PEN',
                        archivo_comprobante VARCHAR(100) NULL,
                        observaciones TEXT NOT NULL DEFAULT '',
                        creado TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                        actualizado TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                        agencia_id BIGINT NOT NULL REFERENCES core_agencia(id) ON DELETE CASCADE,
                        factura_id BIGINT NULL REFERENCES finance_facturaconsolidada(id) ON DELETE SET NULL
                    );
                    CREATE INDEX IF NOT EXISTS finance_retencionislr_agencia_estado
                        ON finance_retencionislr (agencia_id, estado);
                    CREATE INDEX IF NOT EXISTS finance_retencionislr_agencia_fecha
                        ON finance_retencionislr (agencia_id, fecha_emision);
                    """,
                    reverse_sql="DROP TABLE IF EXISTS finance_retencionislr;",
                ),
            ],
            state_operations=[
                migrations.AlterModelOptions(
                    name="retencionislr",
                    options={
                        "ordering": ["-fecha_emision"],
                        "verbose_name": "Retención ISLR",
                        "verbose_name_plural": "Retenciones ISLR",
                    },
                ),
            ],
        ),
    ]

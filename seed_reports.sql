CREATE TABLE IF NOT EXISTS reports_reportekpi (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'general',
    periodo VARCHAR(30) NOT NULL DEFAULT 'mensual',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agencia_id BIGINT REFERENCES core_agencia(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports_kpisnapshot (
    id BIGSERIAL PRIMARY KEY,
    metrica VARCHAR(40) NOT NULL,
    valor NUMERIC(14,2) NOT NULL,
    fecha DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agencia_id BIGINT REFERENCES core_agencia(id) ON DELETE CASCADE,
    UNIQUE(agencia_id, metrica, fecha)
);

CREATE TABLE IF NOT EXISTS reports_reporteprogramado (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'general',
    frecuencia VARCHAR(20) NOT NULL DEFAULT 'semanal',
    dia_semana INTEGER,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    destinatarios JSONB NOT NULL DEFAULT '[]',
    ultimo_envio TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agencia_id BIGINT REFERENCES core_agencia(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kpisnapshot_agencia ON reports_kpisnapshot(agencia_id, fecha DESC);

INSERT INTO django_migrations (app, name, applied) VALUES ('reports', '0001_initial', NOW()) ON CONFLICT DO NOTHING;

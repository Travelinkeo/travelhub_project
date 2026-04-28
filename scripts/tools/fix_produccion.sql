-- Fix para producción: Aumentar campos varchar(100) a varchar(200)
-- Ejecutar en Render Shell: psql $DATABASE_URL < fix_produccion.sql

BEGIN;

-- Aumentar aerolinea_emisora
ALTER TABLE core_boletoimportado 
ALTER COLUMN aerolinea_emisora TYPE varchar(200);

-- Aumentar agente_emisor
ALTER TABLE core_boletoimportado 
ALTER COLUMN agente_emisor TYPE varchar(200);

-- Aumentar direccion_aerolinea (por si acaso)
ALTER TABLE core_boletoimportado 
ALTER COLUMN direccion_aerolinea TYPE text;

COMMIT;

-- Verificar cambios
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'core_boletoimportado' 
AND column_name IN ('aerolinea_emisora', 'agente_emisor', 'direccion_aerolinea');

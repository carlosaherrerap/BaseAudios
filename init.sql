-- ============================================================
-- AUDIOSDB · init.sql
-- Script único de inicialización ejecutado por Docker
-- al primer arranque (docker-entrypoint-initdb.d)
--
-- Usuario : audios_user
-- Puerto  : 5439 (externo) → 5432 (interno)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ============================================================
-- TABLA PRINCIPAL (PARENT) - PARTICIONADA
-- ============================================================
CREATE TABLE IF NOT EXISTS "AUDIOS" (
    id                BIGSERIAL,
    "MES"             TEXT,
    "DIA"             TEXT,
    "INDICE"          TEXT,
    "YEAR"            TEXT,
    "COD1"            TEXT,
    "AoP"             TEXT,
    "COD2"            TEXT,
    "COD3"            TEXT,
    "TELEFONO"        TEXT,
    "PESO"            TEXT,
    "RUTA"            TEXT,
    "NOMBRE_COMPLETO" TEXT,
    "BLOQUE_7"        TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    -- Es un requerimiento en PostgreSQL que la clave de partición esté en el primary key
    PRIMARY KEY (id, "MES")
) PARTITION BY LIST ("MES");

-- ============================================================
-- 12 TABLAS HIJAS (PARTICIONES POR MES)
-- ============================================================
CREATE TABLE "AUDIOS_ENERO"      PARTITION OF "AUDIOS" FOR VALUES IN ('ENERO', 'Enero', 'enero', '1', '01');
CREATE TABLE "AUDIOS_FEBRERO"    PARTITION OF "AUDIOS" FOR VALUES IN ('FEBRERO', 'Febrero', 'febrero', '2', '02');
CREATE TABLE "AUDIOS_MARZO"      PARTITION OF "AUDIOS" FOR VALUES IN ('MARZO', 'Marzo', 'marzo', '3', '03');
CREATE TABLE "AUDIOS_ABRIL"      PARTITION OF "AUDIOS" FOR VALUES IN ('ABRIL', 'Abril', 'abril', '4', '04');
CREATE TABLE "AUDIOS_MAYO"       PARTITION OF "AUDIOS" FOR VALUES IN ('MAYO', 'Mayo', 'mayo', '5', '05');
CREATE TABLE "AUDIOS_JUNIO"      PARTITION OF "AUDIOS" FOR VALUES IN ('JUNIO', 'Junio', 'junio', '6', '06');
CREATE TABLE "AUDIOS_JULIO"      PARTITION OF "AUDIOS" FOR VALUES IN ('JULIO', 'Julio', 'julio', '7', '07');
CREATE TABLE "AUDIOS_AGOSTO"     PARTITION OF "AUDIOS" FOR VALUES IN ('AGOSTO', 'Agosto', 'agosto', '8', '08');
CREATE TABLE "AUDIOS_SEPTIEMBRE" PARTITION OF "AUDIOS" FOR VALUES IN ('SEPTIEMBRE', 'Septiembre', 'septiembre', '9', '09');
CREATE TABLE "AUDIOS_OCTUBRE"    PARTITION OF "AUDIOS" FOR VALUES IN ('OCTUBRE', 'Octubre', 'octubre', '10');
CREATE TABLE "AUDIOS_NOVIEMBRE"  PARTITION OF "AUDIOS" FOR VALUES IN ('NOVIEMBRE', 'Noviembre', 'noviembre', '11');
CREATE TABLE "AUDIOS_DICIEMBRE"  PARTITION OF "AUDIOS" FOR VALUES IN ('DICIEMBRE', 'Diciembre', 'diciembre', '12');

-- ============================================================
-- ÍNDICES DE ALTO RENDIMIENTO EN LA TABLA PADRE
-- (PostgreSQL creará automáticamente estos índices en las particiones hijas)
-- ============================================================

-- Índice principal por TELEFONO con TEXT_PATTERN_OPS (Hiper-rápido para búsquedas LIKE 'prefix%')
CREATE INDEX IF NOT EXISTS idx_audios_telefono_pattern
    ON "AUDIOS" ("TELEFONO" text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_audios_year_mes_dia
    ON "AUDIOS" ("YEAR", "MES", "DIA");

CREATE INDEX IF NOT EXISTS idx_audios_cod1 ON "AUDIOS" ("COD1");
CREATE INDEX IF NOT EXISTS idx_audios_cod2 ON "AUDIOS" ("COD2");
CREATE INDEX IF NOT EXISTS idx_audios_cod3 ON "AUDIOS" ("COD3");

-- ============================================================
-- COMENTARIOS
-- ============================================================
COMMENT ON TABLE  "AUDIOS"              IS 'Registros de audio particionados por MES';
COMMENT ON COLUMN "AUDIOS"."TELEFONO"   IS 'Campo principal de búsqueda desde el frontend';
COMMENT ON COLUMN "AUDIOS"."RUTA"       IS 'Ruta absoluta del archivo de audio en disco';

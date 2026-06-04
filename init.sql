-- ============================================================
-- AUDIOSDB · init.sql
-- Script único de inicialización ejecutado por Docker
-- al primer arranque (docker-entrypoint-initdb.d)
--
-- Usuario : audios_user
-- Puerto  : 5439 (externo) → 5432 (interno)
-- Tabla   : AUDIOS  (optimizada para 10M+ registros)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ============================================================
-- TABLA PRINCIPAL
-- ============================================================
CREATE TABLE IF NOT EXISTS "AUDIOS" (
    id                BIGSERIAL        PRIMARY KEY,
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
    "NOMBRE_COMPLETO" TEXT,                        -- Nombre del archivo
    "BLOQUE_7"        TEXT,
    created_at        TIMESTAMPTZ      DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES DE ALTO RENDIMIENTO
-- ============================================================

-- 1. Índice principal por TELEFONO (campo de búsqueda del frontend)
CREATE INDEX IF NOT EXISTS idx_audios_telefono
    ON "AUDIOS" ("TELEFONO");

-- 2. Covering index: TELEFONO + columnas devueltas frecuentemente
CREATE INDEX IF NOT EXISTS idx_audios_telefono_covering
    ON "AUDIOS" ("TELEFONO")
    INCLUDE ("NOMBRE_COMPLETO", "MES", "DIA", "YEAR", "RUTA", "PESO");

-- 3. Índice compuesto por fecha
CREATE INDEX IF NOT EXISTS idx_audios_year_mes_dia
    ON "AUDIOS" ("YEAR", "MES", "DIA");

-- 4. Índices auxiliares
CREATE INDEX IF NOT EXISTS idx_audios_cod1 ON "AUDIOS" ("COD1");
CREATE INDEX IF NOT EXISTS idx_audios_cod2 ON "AUDIOS" ("COD2");
CREATE INDEX IF NOT EXISTS idx_audios_cod3 ON "AUDIOS" ("COD3");

-- ============================================================
-- COMENTARIOS
-- ============================================================
COMMENT ON TABLE  "AUDIOS"              IS 'Registros de audio — optimizado para 10M+ filas';
COMMENT ON COLUMN "AUDIOS"."TELEFONO"   IS 'Campo principal de búsqueda desde el frontend';
COMMENT ON COLUMN "AUDIOS"."YEAR"       IS 'Fecha completa formato YYYYMMDD (ej: 20260102)';
COMMENT ON COLUMN "AUDIOS"."RUTA"       IS 'Ruta absoluta del archivo de audio en disco';
COMMENT ON COLUMN "AUDIOS"."PESO"       IS 'Duración o tamaño del archivo de audio';

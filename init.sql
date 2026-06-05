CREATE EXTENSION IF NOT EXISTS pg_stat_statements;


DO $$ 
DECLARE
    meses TEXT[] := ARRAY['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'];
    mes TEXT;
BEGIN
    FOREACH mes IN ARRAY meses LOOP
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS "AUDIOS_%s" (
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
                "NOMBRE_COMPLETO" TEXT,
                "BLOQUE_7"        TEXT,
                created_at        TIMESTAMPTZ      DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_audios_%s_telefono_pattern 
                ON "AUDIOS_%s" ("TELEFONO" text_pattern_ops);
                
            CREATE INDEX IF NOT EXISTS idx_audios_%s_year_mes_dia 
                ON "AUDIOS_%s" ("YEAR", "MES", "DIA");
        ', mes, mes, mes, mes, mes);
    END LOOP;
END $$;

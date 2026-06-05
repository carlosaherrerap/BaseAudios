import os
import sys
import logging
import math
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from tqdm import tqdm
from pandas import isna as pd_isna

# ── Configuración de logging ───────────────────────────────────────────────────
# Forzar UTF-8 en stdout para evitar UnicodeEncodeError en Windows (cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("import.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Cargar variables de entorno (.env) ─────────────────────────────────────────
load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME",     "AUDIOSDB"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# ── Configuración del Excel ────────────────────────────────────────────────────
EXCEL_FILE   = os.getenv("EXCEL_FILE", "reporte_enero.xlsx")
_sheet_raw   = os.getenv("SHEET_NAME", "0")
SHEET_NAME   = int(_sheet_raw) if _sheet_raw.isdigit() else _sheet_raw  # 0 = primera hoja
BATCH_SIZE   = int(os.getenv("BATCH_SIZE", 5000))  # filas por lote

# Mes objetivo para la tabla particionada (ej: ENERO, FEBRERO, etc.)
TARGET_MES   = os.getenv("TARGET_MES", "ENERO").upper().strip()
TARGET_TABLE = f"AUDIOS_{TARGET_MES}"

# Columnas esperadas A→M (13 columnas)
EXPECTED_COLUMNS = [
    "MES", "DIA", "INDICE", "YEAR", "COD1",
    "AoP", "COD2", "COD3", "TELEFONO", "PESO",
    "RUTA", "NOMBRE_COMPLETO", "BLOQUE_7"
]

# ── SQL de inserción ───────────────────────────────────────────────────────────
INSERT_SQL = f"""
    INSERT INTO "{TARGET_TABLE}" (
        "MES", "DIA", "INDICE", "YEAR", "COD1",
        "AoP", "COD2", "COD3", "TELEFONO", "PESO",
        "RUTA", "NOMBRE_COMPLETO", "BLOQUE_7"
    ) VALUES %s
    ON CONFLICT DO NOTHING
"""


def clean_value(val):
    """Convierte NaN/NaT/pd.NA a None y limpia espacios en strings.

    psycopg2 no sabe manejar pd.NA (NAType de pandas nullable integers),
    por eso todo valor nulo se convierte explícitamente a None de Python.
    """
    # Captura: None, float('nan'), pd.NA, pd.NaT, numpy.nan
    try:
        if pd_isna(val):
            return None
    except (TypeError, ValueError):
        pass  # pd_isna lanza TypeError con algunos tipos — ignorar
    if isinstance(val, str):
        val = val.strip()
        return val if val else None
    return val


def read_excel(path: str) -> pd.DataFrame:
    """Lee el Excel y valida que tenga las 13 columnas esperadas."""
    logger.info(f"Leyendo archivo: {path}")
    excel_path = Path(path)

    if not excel_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {excel_path.resolve()}")

    # Mostrar hojas disponibles para facilitar debugging
    import openpyxl
    wb_peek = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    sheet_names = wb_peek.sheetnames
    wb_peek.close()
    logger.info(f"Hojas disponibles en el Excel: {sheet_names}")
    logger.info(f"Usando hoja: {SHEET_NAME!r}")

    try:
        df = pd.read_excel(
            excel_path,
            sheet_name=SHEET_NAME,
            usecols="A:M",      # Solo columnas A hasta M
            dtype=str,          # Leer todo como string primero
            engine="openpyxl",
        )
    except Exception as e:
        raise ValueError(
            f"No se pudo leer la hoja {SHEET_NAME!r}. "
            f"Hojas disponibles: {sheet_names}. "
            f"Ajusta SHEET_NAME en el .env al nombre exacto o al índice numérico. Error: {e}"
        ) from e

    # Normalizar nombres de columnas (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]

    logger.info(f"Columnas encontradas en Excel: {list(df.columns)}")
    logger.info(f"Total de filas leídas: {len(df):,}")

    # Renombrar columnas si coinciden por posición (por si los headers difieren levemente)
    if len(df.columns) == 13:
        df.columns = EXPECTED_COLUMNS
        logger.info("Columnas mapeadas a los nombres estándar.")
    else:
        raise ValueError(
            f"Se esperaban 13 columnas (A–M), pero se encontraron {len(df.columns)}. "
            f"Columnas: {list(df.columns)}"
        )

    # Eliminar filas completamente vacías
    df.dropna(how="all", inplace=True)
    logger.info(f"Filas válidas tras limpieza: {len(df):,}")

    # Forzar el mes de la variable de entorno para asegurar que inserte en la tabla correcta
    df['MES'] = TARGET_MES
    
    return df


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """No realizamos conversiones numéricas ya que todas las columnas son texto/VARCHAR en la base de datos."""
    return df


def insert_batches(df: pd.DataFrame, conn) -> int:
    """Inserta los datos en lotes usando execute_values (muy eficiente)."""
    total_rows     = len(df)
    inserted_total = 0

    with conn.cursor() as cur:
        batches = range(0, total_rows, BATCH_SIZE)
        for start in tqdm(batches, desc="Insertando lotes", unit="lote"):
            batch = df.iloc[start : start + BATCH_SIZE]

            records = [
                tuple(clean_value(row[col]) for col in EXPECTED_COLUMNS)
                for _, row in batch.iterrows()
            ]

            try:
                psycopg2.extras.execute_values(
                    cur,
                    INSERT_SQL,
                    records,
                    template=None,
                    page_size=BATCH_SIZE,
                )
                conn.commit()
                inserted_total += len(records)
            except psycopg2.Error as e:
                conn.rollback()
                logger.error(f"Error en lote {start}–{start + BATCH_SIZE}: {e}")
                raise

    return inserted_total


def main():
    # 1. Leer Excel
    try:
        df = read_excel(EXCEL_FILE)
        df = convert_types(df)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    # 2. Conectar a PostgreSQL
    logger.info(f"Conectando a PostgreSQL -> {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        logger.info("Conexión exitosa.")
    except psycopg2.OperationalError as e:
        logger.error(f"No se pudo conectar a PostgreSQL: {e}")
        sys.exit(1)

    # 3. Insertar datos
    try:
        total_insertados = insert_batches(df, conn)
        logger.info(f"✅ Importación completada: {total_insertados:,} registros insertados.")
    except Exception as e:
        logger.error(f"Importación fallida: {e}")
        sys.exit(1)
    finally:
        conn.close()
        logger.info("Conexión cerrada.")


if __name__ == "__main__":
    main()

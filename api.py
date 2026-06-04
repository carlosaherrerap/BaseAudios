"""
api.py
======
API REST mínima con Flask para servir búsquedas por TELEFONO.
Optimizada con paginación y query parametrizada.

Instalación:
    pip install flask flask-cors psycopg2-binary python-dotenv
Ejecución:
    python api.py
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permite peticiones desde el HTML en cualquier origen

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME",     "AUDIOSDB"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

PAGE_SIZE = 50   # Máximo de resultados por página


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


@app.route("/api/buscar", methods=["GET"])
def buscar():
    """
    Búsqueda por TELEFONO.
    Query params:
        q     → número de teléfono (parcial o completo)
        page  → página de resultados (default: 1)
    """
    query  = request.args.get("q", "").strip()
    page   = max(1, int(request.args.get("page", 1)))
    offset = (page - 1) * PAGE_SIZE

    if not query:
        return jsonify({"error": "El parámetro 'q' es requerido."}), 400

    if len(query) < 3:
        return jsonify({"error": "Ingresa al menos 3 caracteres."}), 400

    sql_data = """
        SELECT
            "MES", "DIA", "INDICE", "YEAR",
            "COD1", "AoP", "COD2", "COD3",
            "TELEFONO", "PESO", "RUTA",
            "NOMBRE_COMPLETO", "BLOQUE_7"
        FROM "AUDIOS"
        WHERE "TELEFONO" LIKE %s
        ORDER BY "YEAR" DESC, "MES" DESC, "DIA" DESC
        LIMIT %s OFFSET %s
    """
    sql_count = """
        SELECT COUNT(*) FROM "AUDIOS" WHERE "TELEFONO" LIKE %s
    """
    param_like = f"{query}%"   # Búsqueda por prefijo → usa el índice B-tree

    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_count, (param_like,))
            total = cur.fetchone()["count"]

            cur.execute(sql_data, (param_like, PAGE_SIZE, offset))
            rows = cur.fetchall()
        conn.close()
    except psycopg2.Error as e:
        logger.error(f"DB error: {e}")
        return jsonify({"error": "Error de base de datos."}), 500

    return jsonify({
        "total":      total,
        "page":       page,
        "page_size":  PAGE_SIZE,
        "pages":      (total + PAGE_SIZE - 1) // PAGE_SIZE,
        "results":    [dict(r) for r in rows],
    })


@app.route("/api/health", methods=["GET"])
def health():
    """Endpoint de salud para verificar que la API está activa."""
    try:
        conn = get_connection()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"})
    except Exception:
        return jsonify({"status": "error", "db": "disconnected"}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

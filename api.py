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

app = Flask(__name__, static_folder=os.path.abspath(os.path.dirname(__file__)), static_url_path='')
CORS(app)  # Permite peticiones desde el HTML en cualquier origen

@app.route("/")
def index():
    return app.send_static_file("index.html")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME",     "AUDIOSDB"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

PAGE_SIZE = 10   # Máximo de resultados por página



def get_connection():
    return psycopg2.connect(**DB_CONFIG)


@app.route("/api/buscar", methods=["GET"])
def buscar():
    """
    Búsqueda por TELEFONO y filtrado opcional por MES.
    Query params:
        q     → número de teléfono (parcial o completo)
        page  → página de resultados (default: 1)
        mes   → mes a buscar o "TODOS" (default: TODOS)
    """
    query  = request.args.get("q", "").strip()
    page   = max(1, int(request.args.get("page", 1)))
    mes    = request.args.get("mes", "TODOS").strip().upper()
    offset = (page - 1) * PAGE_SIZE

    if not query:
        return jsonify({"error": "El parámetro 'q' es requerido."}), 400

    if len(query) < 3:
        return jsonify({"error": "Ingresa al menos 3 caracteres."}), 400

    # Construcción de la consulta dinámica
    where_clauses = ['"TELEFONO" LIKE %s']
    params = [f"{query}%"]

    if mes != "TODOS":
        where_clauses.append('"MES" = %s')
        params.append(mes)

    where_sql = " AND ".join(where_clauses)

    sql_data = f"""
        SELECT
            "MES", "DIA", "INDICE", "YEAR",
            "COD1", "AoP", "COD2", "COD3",
            "TELEFONO", "PESO", "RUTA",
            "NOMBRE_COMPLETO", "BLOQUE_7"
        FROM "AUDIOS"
        WHERE {where_sql}
        ORDER BY "YEAR" DESC, "MES" DESC, "DIA" DESC
        LIMIT %s OFFSET %s
    """
    sql_count = f"""
        SELECT COUNT(*) FROM "AUDIOS" WHERE {where_sql}
    """
    
    params_data = params + [PAGE_SIZE, offset]

    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_count, tuple(params))
            total = cur.fetchone()["count"]

            cur.execute(sql_data, tuple(params_data))
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


from flask import send_file

@app.route("/api/health", methods=["GET"])
def health():
    """Endpoint de salud para verificar que la API está activa."""
    try:
        conn = get_connection()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"})
    except Exception:
        return jsonify({"status": "error", "db": "disconnected"}), 503

@app.route("/api/audio", methods=["GET"])
def serve_audio():
    """Sirve archivos de audio desde el disco local para evadir bloqueos de CORS/Seguridad del navegador."""
    audio_path = request.args.get("path")
    if not audio_path:
        return jsonify({"error": "Parámetro 'path' es requerido."}), 400
        
    # Verificar que el archivo existe
    if not os.path.exists(audio_path) or not os.path.isfile(audio_path):
        return jsonify({"error": "Archivo no encontrado."}), 404
        
    try:
        return send_file(audio_path, conditional=True)
    except Exception as e:
        logger.error(f"Error sirviendo audio {audio_path}: {e}")
        return jsonify({"error": "Error al leer el archivo de audio."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

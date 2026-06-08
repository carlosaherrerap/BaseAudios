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



def get_modified_path(original_path, target="evidencias"):
    if not original_path:
        return ""
    # Normalize all slashes to backslashes
    normalized = original_path.replace('/', '\\')
    parts = [p for p in normalized.split('\\') if p]
    # Filter out 'example' (case-insensitive)
    parts_clean = [p for p in parts if p.lower() != 'example']
    
    if len(parts_clean) >= 2:
        # Prepend 'speechToText_' to the second to last directory
        parts_clean[-2] = f"speechToText_{parts_clean[-2]}"
        # Replace the last element (ID) with the target folder name
        new_parts = parts_clean[:-1] + [target]
        
        prefix = ""
        if original_path.startswith('\\\\'):
            prefix = "\\\\"
        elif original_path.startswith('\\'):
            prefix = "\\"
        return prefix + '\\'.join(new_parts)
        
    return original_path


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def parse_peso(peso_str):
    if not peso_str:
        return 0.0
    try:
        # Extract only digits and decimal points
        clean = "".join(c for c in str(peso_str) if c.isdigit() or c == '.')
        return float(clean) if clean else 0.0
    except ValueError:
        return 0.0


@app.route("/api/buscar", methods=["GET"])
def buscar():
    query  = request.args.get("q", "").strip()
    page   = max(1, int(request.args.get("page", 1)))
    mes    = request.args.get("mes", "TODOS").strip().upper()
    sort   = request.args.get("sort", "DEFAULT").strip().upper()

    if not query:
        return jsonify({"error": "El parámetro 'q' es requerido."}), 400
    if len(query) < 3:
        return jsonify({"error": "Ingresa al menos 3 caracteres."}), 400

    meses = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

    tables_to_query = []
    if mes == "TODOS":
        tables_to_query = [f'"AUDIOS_{m}"' for m in meses]
    else:
        tables_to_query = [f'"AUDIOS_{mes}"']

    where_sql = '"TELEFONO" LIKE %s'
    param_like = f"{query}%"

    # Construir SQL dinámico para soportar 1 o 12 tablas
    select_parts = []
    count_parts = []
    
    for table in tables_to_query:
        select_parts.append(f"""
            SELECT
                "MES", "DIA", "INDICE", "YEAR",
                "COD1", "AoP", "COD2", "COD3",
                "TELEFONO", "PESO", "RUTA",
                "NOMBRE_COMPLETO", "BLOQUE_7"
            FROM {table}
            WHERE {where_sql}
        """)
        count_parts.append(f"SELECT COUNT(*) as c FROM {table} WHERE {where_sql}")

    # Unir todas las consultas con UNION ALL.
    # Usamos un límite alto de seguridad en base de datos para realizar la ordenación completa en memoria
    sql_data = " UNION ALL ".join(select_parts) + """
        ORDER BY "YEAR" DESC, "MES" DESC, "DIA" DESC
        LIMIT 10000
    """
    
    sql_count = f"SELECT SUM(c) as count FROM ({' UNION ALL '.join(count_parts)}) as total_counts"

    # Duplicar el parámetro para cada tabla en el UNION
    params_data = [param_like] * len(tables_to_query)
    params_count = [param_like] * len(tables_to_query)

    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_count, tuple(params_count))
            res = cur.fetchone()
            total = res["count"] if res and res["count"] else 0

            cur.execute(sql_data, tuple(params_data))
            rows = cur.fetchall()
        conn.close()
    except psycopg2.Error as e:
        logger.error(f"DB error: {e}")
        return jsonify({"error": "Error de base de datos."}), 500

    results = []
    for r in rows:
        row_dict = dict(r)
        ruta_str = str(row_dict.get("RUTA") or "").strip()
        nombre_str = str(row_dict.get("NOMBRE_COMPLETO") or "").strip()
        
        # Combine RUTA and NOMBRE_COMPLETO for AUDIO field
        if ruta_str and nombre_str:
            if not (ruta_str.endswith("\\") or ruta_str.endswith("/")):
                audio_path = f"{ruta_str}\\{nombre_str}"
            else:
                audio_path = f"{ruta_str}{nombre_str}"
        else:
            audio_path = ruta_str or nombre_str
            
        # Check gestion status (.txt file presence)
        gestion_status = "yellow"
        if ruta_str and nombre_str:
            filename = f"{nombre_str}.txt"
            
            # Check in 'evidencias' folder
            evidencias_dir = get_modified_path(ruta_str, "evidencias")
            evidencias_file = os.path.join(evidencias_dir, filename)
            
            # Check in 'filtrado' folder
            filtrado_dir = get_modified_path(ruta_str, "filtrado")
            filtrado_file = os.path.join(filtrado_dir, filename)
            
            if os.path.exists(evidencias_file) and os.path.isfile(evidencias_file):
                gestion_status = "green"
            elif os.path.exists(filtrado_file) and os.path.isfile(filtrado_file):
                gestion_status = "red"
                
        row_dict["audio_path"] = audio_path
        row_dict["gestion"] = gestion_status
        results.append(row_dict)

    # Aplicar ordenación en memoria en Python
    if sort == "PESO":
        results.sort(key=lambda x: parse_peso(x.get("PESO")), reverse=True)
    elif sort == "GESTION":
        # Ordenación: verde (0) primero, rojo (1) segundo, amarillo (2) tercero
        results.sort(key=lambda x: 0 if x["gestion"] == "green" else (1 if x["gestion"] == "red" else 2))

    # Paginación manual en memoria
    offset = (page - 1) * PAGE_SIZE
    paginated_results = results[offset : offset + PAGE_SIZE]

    return jsonify({
        "total":      total,
        "page":       page,
        "page_size":  PAGE_SIZE,
        "pages":      (total + PAGE_SIZE - 1) // PAGE_SIZE,
        "results":    paginated_results,
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

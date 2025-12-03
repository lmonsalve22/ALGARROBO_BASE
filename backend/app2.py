import os
import psycopg2
import psycopg2.extras
import bcrypt
import secrets
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- CONFIGURACIÓN ---
DB_CONNECTION_STRING = "postgresql://neondb_owner:npg_xHS7sA1FDPqI@ep-hidden-grass-a4sa46kc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
app = Flask(__name__)
CORS(app)

print("Backend Municipal (versión simple sin JWT) iniciando...")

# Sesiones simples en memoria
active_sessions = {}   # { token: user_id }


# -------------------------------
#  FUNCIONES AUXILIARES
# -------------------------------
def get_db_connection():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        return conn
    except Exception as e:
        print("Error BD:", e)
        return None


def session_required(f):
    """Protege endpoints usando token simple"""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"message": "Token requerido"}), 401

        if token not in active_sessions:
            return jsonify({"message": "Sesión inválida o expirada"}), 401

        user_id = active_sessions[token]
        return f(user_id, *args, **kwargs)

    return decorated


# -------------------------------
#  HOME
# -------------------------------
@app.route("/")
def home():
    return jsonify({"message": "API Municipal funcionando (modo simple)"})


# -------------------------------
#  LOGIN / LOGOUT
# -------------------------------
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or "email" not in data or "password" not in data:
        return jsonify({"message": "Credenciales incompletas"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, password_hash, nombre, nivel_acceso
        FROM users
        WHERE email = %s
    """, (data["email"],))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        return jsonify({"message": "Usuario no encontrado"}), 404

    user_id, stored_hash, nombre, nivel_acceso = user

    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode()

    if not bcrypt.checkpw(data["password"].encode(), stored_hash):
        return jsonify({"message": "Contraseña incorrecta"}), 401

    # Generar token simple
    token = secrets.token_hex(32)
    active_sessions[token] = user_id

    return jsonify({
        "token": token,
        "user": {
            "id": user_id,
            "nombre": nombre,
            "nivel_acceso": nivel_acceso
        }
    })


@app.route("/auth/logout", methods=["POST"])
@session_required
def logout(current_user_id):
    token = request.headers.get("Authorization")

    if token in active_sessions:
        del active_sessions[token]

    return jsonify({"message": "Sesión cerrada"})


# -------------------------------
#  USUARIOS
# -------------------------------
@app.route("/users", methods=["GET"])
@session_required
def get_users(current_user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT u.user_id, u.email, u.nombre, u.nivel_acceso,
               d.nombre AS division, u.activo
        FROM users u
        LEFT JOIN divisiones d ON u.division_id = d.division_id
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(data)


@app.route("/users", methods=["POST"])
@session_required
def create_user(current_user_id):
    data = request.get_json()

    required = ["email", "password", "nombre", "nivel_acceso", "division_id"]
    if not all(k in data for k in required):
        return jsonify({"message": "Datos incompletos"}), 400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (email, password_hash, nombre, nivel_acceso, division_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
        """, (data["email"], hashed, data["nombre"], data["nivel_acceso"], data["division_id"]))

        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Usuario creado", "user_id": new_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# -------------------------------
#  PROYECTOS
# -------------------------------
@app.route("/proyectos", methods=["GET"])
@session_required
def get_proyectos(current_user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM proyectos ORDER BY nombre")
    data = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(data)


@app.route("/proyectos", methods=["POST"])
@session_required
def create_proyecto(current_user_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "Datos vacíos"}), 400

    cols = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    sql = f"INSERT INTO proyectos ({cols}) VALUES ({placeholders}) RETURNING id"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(sql, tuple(data.values()))
        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Proyecto creado", "proyecto_id": new_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/proyectos/<int:pid>", methods=["PUT"])
@session_required
def update_proyecto(current_user_id, pid):
    data = request.get_json()
    if not data:
        return jsonify({"message": "Sin datos"}), 400

    fields = ", ".join([f"{k}=%s" for k in data])
    sql = f"UPDATE proyectos SET {fields} WHERE id=%s"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(sql, (*data.values(), pid))
        conn.commit()
        return jsonify({"message": "Proyecto actualizado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/proyectos/<int:pid>", methods=["DELETE"])
@session_required
def delete_proyecto(current_user_id, pid):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM proyectos WHERE id=%s", (pid,))
        conn.commit()
        return jsonify({"message": "Proyecto eliminado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# -------------------------------
#  DOCUMENTOS
# -------------------------------
@app.route("/proyectos/<int:pid>/documentos", methods=["POST"])
@session_required
def add_doc(current_user_id, pid):
    data = request.get_json()

    if not data or "nombre_archivo" not in data or "url_archivo" not in data:
        return jsonify({"message": "Datos incompletos"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO documentos (proyecto_id, nombre_archivo, url_archivo)
            VALUES (%s, %s, %s)
            RETURNING doc_id
        """, (pid, data["nombre_archivo"], data["url_archivo"]))

        doc_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Documento agregado", "doc_id": doc_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/proyectos/<int:pid>/documentos", methods=["GET"])
@session_required
def get_docs(current_user_id, pid):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM documentos WHERE proyecto_id=%s ORDER BY fecha_subida DESC", (pid,))
    data = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(data)


# -------------------------------
#  EJECUCIÓN
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

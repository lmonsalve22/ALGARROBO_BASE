# app.py
import os
import traceback
import psycopg2
import psycopg2.extras
import bcrypt
import secrets
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# -----------------------
# CONFIG
# -----------------------
DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_xHS7sA1FDPqI@ep-hidden-grass-a4sa46kc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
)
APP_HOST = "0.0.0.0"
APP_PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")

app = Flask(__name__)
CORS(app)

print("Backend Municipal (versión mejorada — sin JWT) iniciando...")

# Sesiones simples en memoria { token: user_id }
active_sessions = {}

# -----------------------
# UTIL: conexión a BD
# -----------------------
def get_db_connection():
    try:
        # Opciones de keepalive pueden ayudar en algunos hostings
        conn = psycopg2.connect(DB_CONNECTION_STRING,
                                keepalives=1,
                                keepalives_idle=30,
                                keepalives_interval=10,
                                keepalives_count=5)
        return conn
    except Exception as e:
        print("Error BD:", e)
        traceback.print_exc()
        return None

# -----------------------
# UTIL: crear tablas si no existen
# -----------------------
def ensure_tables():
    conn = get_db_connection()
    if not conn:
        print("No se pudo conectar a la BD para crear tablas.")
        return

    ddl = [
        """
        CREATE TABLE IF NOT EXISTS divisiones (
            division_id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            nivel_acceso TEXT NOT NULL,
            division_id INTEGER REFERENCES divisiones(division_id),
            activo BOOLEAN DEFAULT TRUE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS proyectos (
            id SERIAL PRIMARY KEY,
            n_registro INTEGER,
            es_prioridad VARCHAR(20),
            area VARCHAR(150),
            lineamiento_estrategico VARCHAR(300),
            financiamiento_municipal VARCHAR(50),
            financiamiento VARCHAR(100),
            nombre TEXT,
            monto NUMERIC,
            estado VARCHAR(100),
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS documentos (
            doc_id SERIAL PRIMARY KEY,
            proyecto_id INTEGER REFERENCES proyectos(id) ON DELETE CASCADE,
            nombre_archivo TEXT,
            url_archivo TEXT,
            fecha_subida TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS auditoria (
            audit_id SERIAL PRIMARY KEY,
            user_id INTEGER,
            accion TEXT,
            descripcion TEXT,
            fecha TIMESTAMP DEFAULT NOW()
        );
        """
    ]

    try:
        cur = conn.cursor()
        for s in ddl:
            cur.execute(s)
        conn.commit()
        cur.close()
    except Exception as e:
        print("Error creando tablas:", e)
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

# Crea tablas al inicio
ensure_tables()

# -----------------------
# UTIL: auditoría
# -----------------------
def log_auditoria(user_id, accion, descripcion):
    try:
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO auditoria (user_id, accion, descripcion) VALUES (%s, %s, %s)",
            (user_id, accion, descripcion)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        traceback.print_exc()

# -----------------------
# DECORADOR: session_required
# -----------------------
def session_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
        elif auth:
            token = auth.strip()

        if not token:
            return jsonify({"message": "Token requerido"}), 401

        if token not in active_sessions:
            return jsonify({"message": "Sesión inválida o expirada"}), 401

        user_id = active_sessions[token]
        return f(user_id, *args, **kwargs)
    return decorated

# -----------------------
# ROUTES
# -----------------------
@app.route("/")
def home():
    return jsonify({"message": "API Municipal funcionando (modo simple, tablas auto-creadas)"})


# AUTH
@app.route("/auth/login2", methods=["POST"])
def login2():
    try:
        data = request.get_json()
        if not data or "email" not in data or "password" not in data:
            return jsonify({"message": "Credenciales incompletas"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a la BD"}), 500

        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, password_hash, nombre, nivel_acceso, activo
            FROM users
            WHERE email = %s
        """, (data["email"],))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            return jsonify({"message": "Usuario no encontrado"}), 404

        user_id, stored_hash, nombre, nivel_acceso, activo = user

        if not activo:
            return jsonify({"message": "Usuario inactivo"}), 403

        # almacenar hash como bytes si viene text
        if isinstance(stored_hash, str):
            stored_hash_b = stored_hash.encode()
        else:
            stored_hash_b = stored_hash

        if not bcrypt.checkpw(data["password"].encode(), stored_hash_b):
            return jsonify({"message": "Contraseña incorrecta"}), 401

        token = secrets.token_hex(32)
        active_sessions[token] = user_id

        log_auditoria(user_id, "login", f"Inicio de sesión desde {request.remote_addr}")

        return jsonify({
            "token": token,
            "user": {
                "id": user_id,
                "nombre": nombre,
                "nivel_acceso": nivel_acceso
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    

@app.route("/auth/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if not data or "email" not in data or "password" not in data:
            return jsonify({"message": "Credenciales incompletas"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a la BD"}), 500

        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # ---------------------------------------
        # 1. OBTENER USUARIO + DIVISIÓN
        # ---------------------------------------
        cur.execute("""
            SELECT 
                u.user_id,
                u.password_hash,
                u.nombre,
                u.nivel_acceso,
                u.activo,
                u.division_id,
                d.nombre AS division_nombre
            FROM users u
            LEFT JOIN divisiones d ON d.division_id = u.division_id
            WHERE u.email = %s
        """, (data["email"],))

        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return jsonify({"message": "Usuario no encontrado"}), 404

        if not user["activo"]:
            cur.close()
            conn.close()
            return jsonify({"message": "Usuario inactivo"}), 403

        # ---------------------------------------
        # 2. VALIDAR CONTRASEÑA
        # ---------------------------------------
        stored_hash = user["password_hash"]
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()

        if not bcrypt.checkpw(data["password"].encode(), stored_hash):
            cur.close()
            conn.close()
            return jsonify({"message": "Contraseña incorrecta"}), 401

        # ---------------------------------------
        # 3. OBTENER ROLES
        # ---------------------------------------
        cur.execute("""
            SELECT r.role_id, r.nombre
            FROM roles r
            INNER JOIN user_roles ur ON ur.role_id = r.role_id
            WHERE ur.user_id = %s
        """, (user["user_id"],))

        roles = [
            {"role_id": row["role_id"], "nombre": row["nombre"]}
            for row in cur.fetchall()
        ]

        # ---------------------------------------
        # 4. ACTUALIZAR FECHA DE ÚLTIMO LOGIN
        # ---------------------------------------
        cur.execute("""
            UPDATE users
            SET fecha_ultimo_login = NOW()
            WHERE user_id = %s
        """, (user["user_id"],))
        conn.commit()

        cur.close()
        conn.close()

        # ---------------------------------------
        # 5. CREAR TOKEN EN MEMORIA
        # ---------------------------------------
        token = secrets.token_hex(32)
        active_sessions[token] = user["user_id"]

        log_auditoria(user["user_id"], "login", f"Inicio de sesión desde {request.remote_addr}")

        # ---------------------------------------
        # 6. RESPUESTA
        # ---------------------------------------
        return jsonify({
            "token": token,
            "user": {
                "id": user["user_id"],
                "nombre": user["nombre"],
                "nivel_acceso": user["nivel_acceso"],
                "division": {
                    "division_id": user["division_id"],
                    "nombre": user["division_nombre"]
                },
                "roles": roles
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500



@app.route("/auth/logout", methods=["POST"])
@session_required
def logout(current_user_id):
    try:
        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
        else:
            token = auth.strip()

        if token in active_sessions:
            del active_sessions[token]

        log_auditoria(current_user_id, "logout", f"Cierre de sesión desde {request.remote_addr}")

        return jsonify({"message": "Sesión cerrada"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500


# USERS
@app.route("/users", methods=["GET"])
@session_required
def get_users(current_user_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT u.user_id, u.email, u.nombre, u.nivel_acceso,
                   d.nombre AS division, u.activo
            FROM users u
            LEFT JOIN divisiones d ON u.division_id = d.division_id
            ORDER BY u.nombre
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception:
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500


@app.route("/users", methods=["POST"])
@session_required
def create_user(current_user_id):
    try:
        data = request.get_json()
        required = ["email", "password", "nombre", "nivel_acceso"]
        if not data or not all(k in data for k in required):
            return jsonify({"message": "Datos incompletos"}), 400

        division_id = data.get("division_id")

        hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (email, password_hash, nombre, nivel_acceso, division_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
        """, (data["email"], hashed, data["nombre"], data["nivel_acceso"], division_id))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        log_auditoria(current_user_id, "create_user", f"Creó user_id={new_id}")

        return jsonify({"message": "Usuario creado", "user_id": new_id}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


@app.route("/users/<int:user_id>", methods=["PUT"])
@session_required
def update_user(current_user_id, user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Sin datos"}), 400

        fields = []
        values = []
        allowed = {"nombre", "email", "nivel_acceso", "division_id", "activo", "password"}

        for k, v in data.items():
            if k not in allowed:
                continue
            if k == "password":
                # actualizar password (hashearla)
                hashed = bcrypt.hashpw(v.encode(), bcrypt.gensalt()).decode()
                fields.append("password_hash = %s")
                values.append(hashed)
            else:
                fields.append(f"{k} = %s")
                values.append(v)

        if not fields:
            return jsonify({"message": "No hay campos válidos para actualizar"}), 400

        values.append(user_id)
        sql = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s"

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        cur = conn.cursor()
        cur.execute(sql, tuple(values))
        conn.commit()
        cur.close()
        conn.close()

        log_auditoria(current_user_id, "update_user", f"Actualizó user_id={user_id}")

        return jsonify({"message": "Usuario actualizado"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


@app.route("/users/<int:user_id>", methods=["DELETE"])
@session_required
def delete_user(current_user_id, user_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not deleted:
            return jsonify({"message": "Usuario no encontrado"}), 404

        log_auditoria(current_user_id, "delete_user", f"Borró user_id={user_id}")

        return jsonify({"message": "Usuario eliminado"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


# DIVISIONES (solo lectura y creación simple)
@app.route("/divisiones", methods=["GET"])
@session_required
def get_divisiones(current_user_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT division_id, nombre FROM divisiones ORDER BY nombre")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception:
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500


@app.route("/divisiones", methods=["POST"])
@session_required
def create_division(current_user_id):
    try:
        data = request.get_json()
        if not data or "nombre" not in data:
            return jsonify({"message": "Nombre requerido"}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        cur = conn.cursor()
        cur.execute("INSERT INTO divisiones (nombre) VALUES (%s) RETURNING division_id", (data["nombre"],))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        log_auditoria(current_user_id, "create_division", f"Creó division_id={new_id}")

        return jsonify({"division_id": new_id}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


# PROYECTOS
@app.route("/proyectos", methods=["GET"])
@session_required
def get_proyectos(current_user_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM proyectos ORDER BY nombre")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception:
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500


@app.route("/proyectos", methods=["POST"])
@session_required
def create_proyecto(current_user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Datos vacíos"}), 400

        # Construir inserción dinámica (validar keys si quieres)
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO proyectos ({cols}) VALUES ({placeholders}) RETURNING id"

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        cur = conn.cursor()
        cur.execute(sql, tuple(data.values()))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        log_auditoria(current_user_id, "create_proyecto", f"Creó proyecto_id={new_id}")

        return jsonify({"message": "Proyecto creado", "proyecto_id": new_id}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


@app.route("/proyectos/<int:pid>", methods=["PUT"])
@session_required
def update_proyecto(current_user_id, pid):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Sin datos"}), 400

        fields = ", ".join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE proyectos SET {fields} WHERE id = %s"

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        cur = conn.cursor()
        cur.execute(sql, (*data.values(), pid))
        conn.commit()
        cur.close()
        conn.close()

        log_auditoria(current_user_id, "update_proyecto", f"Actualizó proyecto_id={pid}")

        return jsonify({"message": "Proyecto actualizado"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


@app.route("/proyectos/<int:pid>", methods=["DELETE"])
@session_required
def delete_proyecto(current_user_id, pid):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        cur = conn.cursor()
        cur.execute("DELETE FROM proyectos WHERE id = %s RETURNING id", (pid,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not deleted:
            return jsonify({"message": "Proyecto no encontrado"}), 404

        log_auditoria(current_user_id, "delete_proyecto", f"Borró proyecto_id={pid}")

        return jsonify({"message": "Proyecto eliminado"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


# DOCUMENTOS
@app.route("/proyectos/<int:pid>/documentos", methods=["POST"])
@session_required
def add_doc(current_user_id, pid):
    try:
        data = request.get_json()
        if not data or "nombre_archivo" not in data or "url_archivo" not in data:
            return jsonify({"message": "Datos incompletos"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO documentos (proyecto_id, nombre_archivo, url_archivo)
            VALUES (%s, %s, %s) RETURNING doc_id
        """, (pid, data["nombre_archivo"], data["url_archivo"]))
        doc_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        log_auditoria(current_user_id, "add_documento", f"Agregó doc_id={doc_id} al proyecto {pid}")

        return jsonify({"message": "Documento agregado", "doc_id": doc_id}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500


@app.route("/proyectos/<int:pid>/documentos", methods=["GET"])
@session_required
def get_docs(current_user_id, pid):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM documentos WHERE proyecto_id = %s ORDER BY fecha_subida DESC", (pid,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception:
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500


# AUDITORÍA
@app.route("/auditoria", methods=["GET"])
@session_required
def get_auditoria(current_user_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT a.audit_id, a.user_id, u.nombre AS usuario, a.accion, a.descripcion, a.fecha
            FROM auditoria a
            LEFT JOIN users u ON a.user_id = u.user_id
            ORDER BY a.fecha DESC
            LIMIT 1000
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception:
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500


# -----------------------
# START
# -----------------------
if __name__ == '__main__':
    cert_path = os.path.abspath("fullchain.pem")
    key_path = os.path.abspath("private.key")
    app.run(host='0.0.0.0', port=8000, ssl_context=(cert_path, key_path))

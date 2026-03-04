
# app21.py - Versión optimizada para Railway Postgres
import os
import traceback
import time
import psycopg2
import psycopg2.extras
import psycopg2.pool
import bcrypt
import logging
import threading
from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
import secrets

from dotenv import load_dotenv

load_dotenv()
# -----------------------
# CONFIGURACIÓN DE LOGGING
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("municipal_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -----------------------
# CONFIG
# -----------------------
DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
if not DB_CONNECTION_STRING:
    raise ValueError("No DATABASE_URL set for Flask application")

APP_HOST = "0.0.0.0"
APP_PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    if request.path.startswith('/api'):
        logger.info(f"REQUEST {request.method} {request.path} -> {response.status_code}")
    
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Access-Control-Allow-Credentials'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    response = jsonify({"error": str(e)})
    response.status_code = 500
    if hasattr(e, 'code'):
        response.status_code = e.code
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Access-Control-Allow-Credentials'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

logger.info("Backend Municipal iniciando...")
# Pool de conexiones global
connection_pool = None
pool_lock = threading.RLock()

# Sesiones
active_sessions = {}
sessions_lock = threading.Lock()
SESSION_EXPIRY_HOURS = 1

# -----------------------
# UTIL: inicialización y gestión del pool de conexiones
# -----------------------
def init_connection_pool(max_retries=1):
    """
    Inicializa el pool de conexiones a la base de datos de manera ligera para Railway
    """
    global connection_pool
    
    try:
        with pool_lock:
            if connection_pool and not connection_pool.closed:
                try:
                    connection_pool.closeall()
                    logger.info("Pool anterior cerrado correctamente")
                except Exception as e:
                    logger.warning(f"Error cerrando pool anterior: {e}")
            
            connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DB_CONNECTION_STRING,
                keepalives=1,
                keepalives_idle=60,
                keepalives_interval=10,
                keepalives_count=5,
                connect_timeout=10,
                application_name="municipal_api_railway"
            )
            
            # Verificar que el pool funciona
            test_conn = connection_pool.getconn()
            with test_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            connection_pool.putconn(test_conn)
            
            logger.info("Pool de conexiones inicializado correctamente (Optimizado para Railway)")
            return True
            
    except Exception as e:
        logger.error(f"Error en la inicialización del pool: {e}")
        connection_pool = None
        return False

def get_db_connection():
    global connection_pool
    
    try:
        if connection_pool is None or connection_pool.closed:
            logger.info("Pool no disponible, inicializando...")
            if not init_connection_pool():
                raise Exception("No se pudo inicializar el pool de conexiones")
        
        conn = connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Error obteniendo conexión: {e}")
        raise e

def release_db_connection(conn):
    try:
        if connection_pool and conn:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error al devolver la conexión al pool: {e}")
        try:
            conn.close()
        except:
            pass

#-------------------------

from extract import extract_text_from_file

# -----------------------
# CONFIG DOCUMENTOS
# -----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_FOLDER = os.path.join(BASE_DIR, "docs")

# Crear carpeta si no existe
os.makedirs(DOCS_FOLDER, exist_ok=True)

# Opcional: extensiones permitidas
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx",
    "png", "jpg", "jpeg", 
    #"zip"
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# MEJORA #4: Funciones de gestión de sesiones con expiración
def create_session(user_id):
    """Crea una nueva sesión con timestamp"""
    token = secrets.token_hex(32)
    now = datetime.now()
    with sessions_lock:
        active_sessions[token] = {
            "user_id": user_id,
            "created_at": now,
            "last_activity": now
        }
    return token

def validate_session(token):
    """Valida sesión y actualiza last_activity. Retorna user_id o None"""
    with sessions_lock:
        session = active_sessions.get(token)
        if not session:
            return None
        
        # Verificar expiración
        if datetime.now() - session["last_activity"] > timedelta(hours=SESSION_EXPIRY_HOURS):
            del active_sessions[token]
            return None
        
        # Actualizar actividad
        session["last_activity"] = datetime.now()
        return session["user_id"]

def remove_session(token):
    """Elimina una sesión"""
    with sessions_lock:
        if token in active_sessions:
            del active_sessions[token]

def cleanup_expired_sessions():
    """Limpia sesiones expiradas - llamar periódicamente"""
    now = datetime.now()
    with sessions_lock:
        expired = [
            t for t, s in active_sessions.items()
            if now - s["last_activity"] > timedelta(hours=SESSION_EXPIRY_HOURS)
        ]
        for t in expired:
            del active_sessions[t]
        if expired:
            logger.info(f"Limpiadas {len(expired)} sesiones expiradas")

# Inicializar pool al inicio
if not init_connection_pool():
    logger.error("No se pudo inicializar el pool de conexiones al inicio")

# -----------------------
# UTIL: MÓDULO DE CONTROL – registro de actividad enriquecido
# -----------------------
def log_control(user_id, accion, modulo='proyectos',
                entidad_tipo=None, entidad_id=None, entidad_nombre=None,
                exitoso=True, detalle=None,
                datos_antes=None, datos_despues=None):
    """
    Registra cada acción del usuario en control_actividad con contexto completo.
    Se llama desde los endpoints de API tras cada operación.
    """
    conn = None
    try:
        import json as _json
        ip = None
        ua = None
        ep = None
        try:
            ip = request.remote_addr
            ua = request.headers.get('User-Agent', '')[:500]
            ep = request.path[:200]
        except RuntimeError:
            pass  # fuera de contexto de request (ej. triggers)

        conn = get_db_connection()
        if not conn:
            return
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO control_actividad
                    (user_id, accion, modulo,
                     entidad_tipo, entidad_id, entidad_nombre,
                     exitoso, detalle,
                     ip_origen, user_agent, endpoint,
                     datos_antes, datos_despues)
                VALUES (%s,%s,%s, %s,%s,%s, %s,%s, %s,%s,%s, %s,%s)
            """, (
                user_id, accion, modulo,
                entidad_tipo, entidad_id, entidad_nombre,
                exitoso, detalle,
                ip, ua, ep,
                _json.dumps(datos_antes) if datos_antes else None,
                _json.dumps(datos_despues) if datos_despues else None
            ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error en log_control: {e}")
    finally:
        if conn:
            release_db_connection(conn)


# -----------------------
# UTIL: auditoría legacy (mantener compatibilidad)
# -----------------------
def log_auditoria(user_id, accion, descripcion):
    """Auditoría legacy + registro en módulo de control."""
    modulo = 'auth' if any(k in accion for k in ('login', 'logout', 'password')) else \
             'usuarios' if 'user' in accion else 'proyectos'
    log_control(user_id, accion, modulo=modulo, detalle=descripcion)
    # Mantener escritura en tabla legacy auditoria
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auditoria (user_id, accion, descripcion) VALUES (%s, %s, %s)",
                (user_id, accion, descripcion)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Error en auditoría legacy: {e}")
    finally:
        if conn:
            release_db_connection(conn)

# -----------------------
# DECORADOR: session_required (MEJORADO con expiración)
# -----------------------
def session_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({}), 200

        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
        elif request.args.get("token"):
            token = request.args.get("token")
        elif auth:
            token = auth.strip()

        if not token:
            return jsonify({"message": "Token requerido"}), 401

        # MEJORA #4: Usar validate_session con expiración automática
        user_id = validate_session(token)
        if user_id is None:
            return jsonify({"message": "Sesión inválida o expirada"}), 401

        return f(user_id, *args, **kwargs)
    return decorated


# -----------------------
# ROUTES
# -----------------------
@app.route("/")
def home():
    return jsonify({"message": "API Municipal funcionando (Optimizado para Railway Postgres)"})

@app.route("/health")
def health_check():
    """Endpoint para verificar el estado de la aplicación y la conexión a la base de datos"""
    try:
        # Verificar el pool de conexiones
        pool_status = {
            "initialized": connection_pool is not None and not connection_pool.closed,
            "min_connections": connection_pool.minconn if connection_pool else None,
            "max_connections": connection_pool.maxconn if connection_pool else None,
            "current_connections": len(connection_pool._pool) if connection_pool else None
        }
        
        # Verificar conexión a la base de datos
        db_status = "disconnected"
        try:
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                db_status = "connected"
                release_db_connection(conn)
        except Exception as e:
            logger.error(f"Error en health check de BD: {e}")
            db_status = f"error: {str(e)}"
        
        # Verificar sesiones activas
        sessions_count = len(active_sessions)
        
        # Determinar estado general
        if db_status == "connected" and pool_status["initialized"]:
            status_code = 200
            status = "healthy"
        else:
            status_code = 503
            status = "unhealthy"
        
        return jsonify({
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "database": {
                "status": db_status,
                "connection_string": DB_CONNECTION_STRING.split("@")[1] if "@" in DB_CONNECTION_STRING else "hidden"
            },
            "connection_pool": pool_status,
            "active_sessions": sessions_count,
            "version": "2.0.0",
            "railway_optimized": True
        }), status_code
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

# AUTH
@app.route("/auth/login2", methods=["POST"])
def login2():
    conn = None
    try:
        data = request.get_json()
        if not data or "email" not in data or "password" not in data:
            return jsonify({"message": "Credenciales incompletas"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a la BD"}), 500

        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, password_hash, nombre, nivel_acceso, activo
                FROM users
                WHERE email = %s
            """, (data["email"],))
            user = cur.fetchone()

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

        # MEJORA #4: Usar create_session con timestamp
        token = create_session(user_id)

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
        logger.error(f"Error en login2: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)
    

@app.route("/auth/login", methods=["POST"])
def login():
    conn = None
    try:
        data = request.get_json()
        if not data or "email" not in data or "password" not in data:
            return jsonify({"message": "Credenciales incompletas"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a la BD"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

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
                return jsonify({"message": "Usuario no encontrado"}), 404

            if not user["activo"]:
                return jsonify({"message": "Usuario inactivo"}), 403

            # ---------------------------------------
            # 2. VALIDAR CONTRASEÑA
            # ---------------------------------------
            stored_hash = user["password_hash"]
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode()

            if not bcrypt.checkpw(data["password"].encode(), stored_hash):
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

        # ---------------------------------------
        # 5. CREAR TOKEN EN MEMORIA (MEJORADO)
        # ---------------------------------------
        token = create_session(user["user_id"])

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
        logger.error(f"Error en login: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)



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

        # MEJORA #4: Usar remove_session
        remove_session(token)

        log_auditoria(current_user_id, "logout", f"Cierre de sesión desde {request.remote_addr}")

        return jsonify({"message": "Sesión cerrada"})
    except Exception as e:
        logger.error(f"Error en logout: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500


# USERS
@app.route("/users", methods=["GET"])
@session_required
def get_users(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT u.user_id, u.email, u.nombre, u.nivel_acceso,
                       d.nombre AS division, d.division_id,
                       u.activo
                FROM users u
                LEFT JOIN divisiones d ON u.division_id = d.division_id
                ORDER BY u.nombre
            """)
            rows = cur.fetchall()
            # Map division_nombre for frontend
            for r in rows:
                r["division_nombre"] = r["division"] # maintain compatibility
        return jsonify(rows)

    except Exception as e:
        logger.error(f"Error en get_users: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)





@app.route("/users", methods=["POST"])
@session_required
def create_user(current_user_id):
    conn = None
    try:
        data = request.get_json()
        required = ["email", "password", "nombre", "nivel_acceso"]
        if not data or not all(k in data for k in required):
            return jsonify({"message": "Datos incompletos"}), 400

        division_id = data.get("division_id")

        hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        
        # Mapear es_activo a activo
        activo = data.get("es_activo", True)

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (email, password_hash, nombre, nivel_acceso, division_id, activo)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """, (data["email"], hashed, data["nombre"], data["nivel_acceso"], division_id, activo))
            new_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "create_user", f"Creó user_id={new_id}")

        return jsonify({"message": "Usuario creado", "user_id": new_id}), 201
    except Exception as e:
        logger.error(f"Error en create_user: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route("/users/<int:user_id>", methods=["PUT"])
@session_required
def update_user(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Sin datos"}), 400

        fields = []
        values = []
        allowed = {"nombre", "email", "nivel_acceso", "division_id", "activo", "password"}

        for k, v in data.items():
            if k == "es_activo": # Mapear es_activo a activo
                fields.append("activo = %s")
                values.append(v)
                continue
            
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
        with conn.cursor() as cur:
            cur.execute(sql, tuple(values))
        conn.commit()

        log_auditoria(current_user_id, "update_user", f"Actualizó user_id={user_id}")

        return jsonify({"message": "Usuario actualizado"})
    except Exception as e:
        logger.error(f"Error en update_user: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route("/users/<int:user_id>", methods=["DELETE"])
@session_required
def delete_user(current_user_id, user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,))
            deleted = cur.fetchone()
        conn.commit()

        if not deleted:
            return jsonify({"message": "Usuario no encontrado"}), 404

        log_auditoria(current_user_id, "delete_user", f"Borró user_id={user_id}")

        return jsonify({"message": "Usuario eliminado"})
    except Exception as e:
        logger.error(f"Error en delete_user: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/users/<int:user_id>", methods=["GET"])
@session_required
def get_user(current_user_id, user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    u.user_id,
                    u.email,
                    u.nombre,
                    u.nivel_acceso,
                    u.activo,
                    u.division_id,
                    d.nombre AS division
                FROM users u
                LEFT JOIN divisiones d ON d.division_id = u.division_id
                WHERE u.user_id = %s
            """, (user_id,))
            user = cur.fetchone()

        if not user:
            return jsonify({"message": "Usuario no encontrado"}), 404

        return jsonify(user)

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/users/<int:user_id>/activar", methods=["PUT"])
@session_required
def activar_usuario(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        activo = data.get("activo")

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET activo = %s
                WHERE user_id = %s
            """, (activo, user_id))
        conn.commit()

        log_auditoria(
            current_user_id,
            "activar_usuario",
            f"Usuario {user_id} activo={activo}"
        )

        return jsonify({"message": "Estado actualizado"})

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/roles", methods=["GET"])
@session_required
def get_roles(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT role_id, nombre FROM roles")
            roles = cur.fetchall()

        return jsonify(roles)

    finally:
        if conn:
            release_db_connection(conn)


@app.route("/users/<int:user_id>/roles", methods=["PUT"])
@session_required
def set_user_roles(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        roles = data.get("roles", [])  # lista de role_id

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
            for role_id in roles:
                cur.execute("""
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (%s, %s)
                """, (user_id, role_id))
        conn.commit()

        log_auditoria(
            current_user_id,
            "set_roles",
            f"Actualizó roles usuario {user_id}"
        )

        return jsonify({"message": "Roles actualizados"})

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/users/<int:user_id>/reset-password", methods=["PUT"])
@session_required
def reset_password(current_user_id, user_id):
    conn = None
    try:
        data = request.get_json()
        new_password = data.get("password")

        hashed = bcrypt.hashpw(
            new_password.encode(),
            bcrypt.gensalt()
        ).decode()

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET password_hash = %s
                WHERE user_id = %s
            """, (hashed, user_id))
        conn.commit()

        log_auditoria(
            current_user_id,
            "reset_password",
            f"Reseteó password usuario {user_id}"
        )

        return jsonify({"message": "Contraseña actualizada"})

    finally:
        if conn:
            release_db_connection(conn)


# DIVISIONES (solo lectura y creación simple)
@app.route("/divisiones", methods=["GET"])
@session_required
def get_divisiones(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT division_id, nombre FROM divisiones")
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error en get_divisiones: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route("/divisiones", methods=["POST"])
@session_required
def create_division(current_user_id):
    conn = None
    try:
        data = request.get_json()
        if not data or "nombre" not in data:
            return jsonify({"message": "Nombre requerido"}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute("INSERT INTO divisiones (nombre) VALUES (%s) RETURNING division_id", (data["nombre"],))
            new_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "create_division", f"Creó division_id={new_id}")

        return jsonify({"division_id": new_id}), 201
    except Exception as e:
        logger.error(f"Error en create_division: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)


# PROYECTOS

@app.route("/proyectos4", methods=["GET"])
@session_required
def get_proyectos4(current_user_id):
    conn = None
    try:
        conn = get_db_connection()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.*,
                    
                    GREATEST(
                        p.fecha_actualizacion,
                        (SELECT MAX(creado_en) FROM proyectos_hitos WHERE proyecto_id = p.id),
                        (SELECT MAX(creado_en) FROM proyectos_observaciones WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_subida) FROM proyectos_documentos WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_creacion) FROM proyectos_geomapas WHERE proyecto_id = p.id)
                    ) AS ult_modificacion,

                    u.nombre AS user_nombre,
                    ua.nombre AS actualizado_por_nombre,

                    a.id AS area_id,
                    a.nombre AS area_nombre,

                    le.id AS lineamiento_id,
                    le.nombre AS lineamiento_nombre,

                    f.id AS financiamiento_id,
                    f.nombre AS financiamiento_nombre,

                    ep.id AS etapa_id,
                    ep.nombre AS etapa_nombre,

                    es.id AS estado_id,
                    es.nombre AS estado_nombre,
                    es.color AS estado_color,

                    epost.id AS estado_postulacion_id,
                    epost.nombre AS estado_postulacion_nombre,

                    s.id AS sector_id,
                    s.nombre AS sector_nombre

                FROM proyectos p
                INNER JOIN users u ON u.user_id = p.user_id
                LEFT JOIN users ua ON ua.user_id = p.actualizado_por

                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN lineamientos_estrategicos le ON le.id = p.lineamiento_estrategico_id
                LEFT JOIN financiamientos f ON f.id = p.financiamiento_id
                LEFT JOIN etapas_proyecto ep ON ep.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                LEFT JOIN estados_postulacion epost ON epost.id = p.estado_postulacion_id
                LEFT JOIN sectores s ON s.id = p.sector_id
            """)

            proyectos = cur.fetchall()

        return jsonify(proyectos)

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos_chat", methods=["GET"])
@session_required
def get_proyectos_chat(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(""" 
                SELECT
                    p.*,
                    
                    GREATEST(
                        p.fecha_actualizacion,
                        (SELECT MAX(creado_en) FROM proyectos_hitos WHERE proyecto_id = p.id),
                        (SELECT MAX(creado_en) FROM proyectos_observaciones WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_subida) FROM proyectos_documentos WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_creacion) FROM proyectos_geomapas WHERE proyecto_id = p.id)
                    ) AS ult_modificacion,
                    a.nombre AS area,
                    le.nombre AS lineamiento,
                    f.nombre AS financiamiento,
                    ep.nombre AS etapa,                  
                    es.nombre AS estado,
                    epost.nombre AS estado_postulacion,
                    s.nombre AS sector                   

                FROM proyectos p

                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN lineamientos_estrategicos le ON le.id = p.lineamiento_estrategico_id
                LEFT JOIN financiamientos f ON f.id = p.financiamiento_id
                LEFT JOIN etapas_proyecto ep ON ep.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                LEFT JOIN estados_postulacion epost ON epost.id = p.estado_postulacion_id
                LEFT JOIN sectores s ON s.id = p.sector_id
            """)
            proyectos = cur.fetchall()

        return jsonify(proyectos)

    finally:
        if conn:
            release_db_connection(conn)


@app.route("/proyectos", methods=["GET"])
@session_required
def get_proyectos(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(""" 
                SELECT
                    p.*,

                    GREATEST(
                        p.fecha_actualizacion,
                        (SELECT MAX(creado_en) FROM proyectos_hitos WHERE proyecto_id = p.id),
                        (SELECT MAX(creado_en) FROM proyectos_observaciones WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_subida) FROM proyectos_documentos WHERE proyecto_id = p.id),
                        (SELECT MAX(fecha_creacion) FROM proyectos_geomapas WHERE proyecto_id = p.id)
                    ) AS ult_modificacion,

                    u.nombre AS user_nombre,
                    ua.nombre AS actualizado_por_nombre,

                    a.id AS area_id,
                    a.nombre AS area_nombre,

                    le.id AS lineamiento_id,
                    le.nombre AS lineamiento_nombre,

                    f.id AS financiamiento_id,
                    f.nombre AS financiamiento_nombre,

                    ep.id AS etapa_id,
                    ep.nombre AS etapa_nombre,

                    es.id AS estado_id,
                    es.nombre AS estado_nombre,
                    es.color AS estado_color,

                    epost.id AS estado_postulacion_id,
                    epost.nombre AS estado_postulacion_nombre,

                    s.id AS sector_id,
                    s.nombre AS sector_nombre,

                    /* 🔽 HITOS */
                    COALESCE(
                        json_agg(
                            DISTINCT jsonb_build_object(
                                'id', h.id,
                                'fecha', h.fecha,
                                'observacion', h.observacion,
                                'creado_por', h.creado_por,
                                'creado_en', h.creado_en
                            )
                        ) FILTER (WHERE h.id IS NOT NULL),
                        '[]'
                    ) AS hitos_lista,

                    /* 🔽 OBSERVACIONES */
                    COALESCE(
                        json_agg(
                            DISTINCT jsonb_build_object(
                                'id', o.id,
                                'fecha', o.fecha,
                                'observacion', o.observacion,
                                'creado_por', o.creado_por,
                                'creado_en', o.creado_en
                            )
                        ) FILTER (WHERE o.id IS NOT NULL),
                        '[]'
                    ) AS observaciones_lista

                FROM proyectos p
                INNER JOIN users u ON u.user_id = p.user_id
                LEFT JOIN users ua ON ua.user_id = p.actualizado_por

                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN lineamientos_estrategicos le ON le.id = p.lineamiento_estrategico_id
                LEFT JOIN financiamientos f ON f.id = p.financiamiento_id
                LEFT JOIN etapas_proyecto ep ON ep.id = p.etapa_proyecto_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                LEFT JOIN estados_postulacion epost ON epost.id = p.estado_postulacion_id
                LEFT JOIN sectores s ON s.id = p.sector_id

                LEFT JOIN proyectos_hitos h ON h.proyecto_id = p.id
                LEFT JOIN proyectos_observaciones o ON o.proyecto_id = p.id

                GROUP BY
                    p.id,
                    u.nombre,
                    ua.nombre,
                    a.id,
                    le.id,
                    f.id,
                    ep.id,
                    es.id,
                    epost.id,
                    s.id;
            """)
            proyectos = cur.fetchall()

        return jsonify(proyectos)

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos_actividad_reciente", methods=["GET"])
@session_required
def get_proyectos_actividad_reciente(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    'proyecto' as tipo,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    a.nombre as area_nombre,
                    p.monto, p.avance_total_porcentaje, es.nombre as estado_nombre,
                    'Proyecto actualizado' as descripcion_actividad,
                    p.fecha_actualizacion as fecha
                FROM proyectos p
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE p.fecha_actualizacion IS NOT NULL

                UNION ALL

                SELECT
                    'documento' as tipo,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    a.nombre as area_nombre,
                    p.monto, p.avance_total_porcentaje, es.nombre as estado_nombre,
                    'Documento subido' || coalesce(': ' || doc.nombre, '') as descripcion_actividad,
                    doc.fecha_subida as fecha
                FROM proyectos_documentos doc
                INNER JOIN proyectos p ON p.id = doc.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE doc.fecha_subida IS NOT NULL

                UNION ALL

                SELECT
                    'hito' as tipo,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    a.nombre as area_nombre,
                    p.monto, p.avance_total_porcentaje, es.nombre as estado_nombre,
                    'Hito creado/modificado' as descripcion_actividad,
                    h.creado_en as fecha
                FROM proyectos_hitos h
                INNER JOIN proyectos p ON p.id = h.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE h.creado_en IS NOT NULL

                UNION ALL

                SELECT
                    'observacion' as tipo,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    a.nombre as area_nombre,
                    p.monto, p.avance_total_porcentaje, es.nombre as estado_nombre,
                    'Observación agregada' as descripcion_actividad,
                    o.creado_en as fecha
                FROM proyectos_observaciones o
                INNER JOIN proyectos p ON p.id = o.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE o.creado_en IS NOT NULL

                UNION ALL

                SELECT
                    'geomapa' as tipo,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    a.nombre as area_nombre,
                    p.monto, p.avance_total_porcentaje, es.nombre as estado_nombre,
                    'Geomapa creado/modificado' || coalesce(': ' || g.nombre, '') as descripcion_actividad,
                    g.fecha_creacion as fecha
                FROM proyectos_geomapas g
                INNER JOIN proyectos p ON p.id = g.proyecto_id
                LEFT JOIN areas a ON a.id = p.area_id
                LEFT JOIN estados_proyecto es ON es.id = p.estado_proyecto_id
                WHERE g.fecha_creacion IS NOT NULL

                ORDER BY fecha DESC
                LIMIT 20;
            """)
            actividad = cur.fetchall()

        return jsonify(actividad)

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos", methods=["POST"])
@session_required
def create_proyecto(current_user_id):
    conn = None
    try:
        data = request.get_json()

        # Remove keys that shouldn't be set directly or are set automatically
        forbidden = {"id", "user_id", "actualizado_por", "fecha_actualizacion", "fecha_creacion"}
        clean_data = {k: v for k, v in data.items() if k not in forbidden and v != ""}

        clean_data["user_id"] = current_user_id
        clean_data["actualizado_por"] = current_user_id
        clean_data["fecha_actualizacion"] = datetime.now()

        if not clean_data:
             return jsonify({"message": "No data provided"}), 400

        cols = ", ".join(clean_data.keys())
        placeholders = ", ".join(["%s"] * len(clean_data))
        
        sql = f"INSERT INTO proyectos ({cols}) VALUES ({placeholders}) RETURNING id"
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(clean_data.values()))
            new_id = cur.fetchone()[0]
            
            # Log audit
            log_auditoria(current_user_id, "create_proyecto", f"Creó proyecto {new_id}: {clean_data.get('nombre')}")
            
        conn.commit()
        return jsonify({"message": "Proyecto creado", "id": new_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error create_proyecto: {e}")
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MODULO: LICITACIONES API
# ============================================

@app.route("/licitaciones/pasos", methods=["POST"])
@session_required
def create_licitacion_paso_maestro(current_user_id):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(orden), 0) FROM licitacion_pasos_maestro")
            next_orden = cur.fetchone()[0] + 1
            cur.execute("""
                INSERT INTO licitacion_pasos_maestro (orden, nombre, descripcion, documento_requerido)
                VALUES (%s, %s, %s, %s)
                RETURNING id_paso
            """, (next_orden, data.get("nombre"), data.get("descripcion"), data.get("documento_requerido")))
            new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Paso maestro creado", "id": new_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/pasos", methods=["GET"])
@session_required
def get_licitacion_pasos_maestro(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM licitacion_pasos_maestro ORDER BY orden")
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error get_licitacion_pasos_maestro: {e}")
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones", methods=["GET"])
@session_required
def get_licitaciones(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT l.*, p.nombre as proyecto_nombre,
                       (SELECT count(*) FROM licitacion_workflow WHERE licitacion_id = l.id AND estado = 'Completado') as pasos_completados
                FROM licitaciones l
                JOIN proyectos p ON p.id = l.proyecto_id
                ORDER BY l.fecha_actualizacion DESC
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error get_licitaciones: {e}")
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/pasos/<int:paso_id>", methods=["PUT"])
@session_required
def update_licitacion_paso_maestro(current_user_id, paso_id):
    conn = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE licitacion_pasos_maestro 
                SET nombre = %s, descripcion = %s, documento_requerido = %s, activo = %s
                WHERE id_paso = %s
            """, (data.get("nombre"), data.get("descripcion"), data.get("documento_requerido"), data.get("activo", True), paso_id))
            
            log_auditoria(current_user_id, "update_paso_maestro", f"Actualizó paso maestro {paso_id}")
            
        conn.commit()
        return jsonify({"message": "Paso maestro actualizado"}), 200
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error update_paso_maestro: {e}")
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones", methods=["POST"])
@session_required
def create_licitacion(current_user_id):
    conn = None
    try:
        data = request.get_json()
        required = ["proyecto_id", "nombre_licitacion"]
        if not data or not all(k in data for k in required):
            return jsonify({"message": "Faltan datos requeridos"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Validar que no exista una licitación abierta para el mismo proyecto
            cur.execute("""
                SELECT id, nombre_licitacion FROM licitaciones 
                WHERE proyecto_id = %s AND COALESCE(estado_licitacion, 'Abierta') = 'Abierta'
            """, (data["proyecto_id"],))
            existing = cur.fetchone()
            if existing:
                return jsonify({
                    "message": f"El proyecto ya tiene una licitación abierta (ID: {existing[0]} - {existing[1]}). Debe cerrarla antes de iniciar una nueva."
                }), 409

            # 1. Crear licitación
            # Limpiar datos opcionales numéricos
            monto = data.get("monto_estimado")
            if monto == "" or monto is None:
                monto = None

            cur.execute("""
                INSERT INTO licitaciones (proyecto_id, nombre_licitacion, id_mercado_publico, monto_estimado, usuario_creador, estado_actual_paso, estado_licitacion)
                VALUES (%s, %s, %s, %s, %s, 1, 'Abierta') RETURNING id
            """, (data["proyecto_id"], data["nombre_licitacion"], data.get("id_mercado_publico"), monto, current_user_id))
            lic_id = cur.fetchone()[0]
            
            # 2. Inicializar workflow (32 pasos)
            cur.execute("""
                INSERT INTO licitacion_workflow (licitacion_id, paso_id, estado)
                SELECT %s, id_paso, 'Pendiente'
                FROM licitacion_pasos_maestro
                ORDER BY orden
            """, (lic_id,))
            
            log_auditoria(current_user_id, "crear_licitacion", f"Inició licitación {lic_id} para proyecto {data['proyecto_id']}")
            
        conn.commit()
        return jsonify({"message": "Licitación iniciada", "id": lic_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error create_licitacion: {e}")
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/<int:lid>", methods=["GET"])
@session_required
def get_licitacion_detalle(current_user_id, lid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT l.*, p.nombre as proyecto_nombre 
                FROM licitaciones l
                JOIN proyectos p ON p.id = l.proyecto_id
                WHERE l.id = %s
            """, (lid,))
            lic = cur.fetchone()
            if not lic: return jsonify({"message": "No encontrada"}), 404
            
            cur.execute("""
                SELECT w.id, w.licitacion_id, w.paso_id, w.estado,
                       w.fecha_planificada::text as fecha_planificada,
                       w.fecha_real::date::text as fecha_real,
                       w.observaciones, w.usuario_id, w.actualizado_en,
                       m.nombre as paso_nombre, m.orden as paso_orden
                FROM licitacion_workflow w
                JOIN licitacion_pasos_maestro m ON m.id_paso = w.paso_id
                WHERE w.licitacion_id = %s
                ORDER BY m.orden
            """, (lid,))
            lic["workflow"] = cur.fetchall()
            
            cur.execute("""
                SELECT d.*, u.nombre as usuario_nombre
                FROM licitaciones_documentos d
                LEFT JOIN users u ON u.user_id = d.usuario_subida
                WHERE d.workflow_id IN (SELECT id FROM licitacion_workflow WHERE licitacion_id = %s)
            """, (lid,))
            docs = cur.fetchall()
            
            for step in lic["workflow"]:
                step["documentos"] = [d for d in docs if d["workflow_id"] == step["id"]]
                
        return jsonify(lic)
    except Exception as e:
        logger.error(f"Error get_licitacion_detalle: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/workflow/<int:wid>", methods=["PUT"])
@session_required
def update_licitacion_workflow(current_user_id, wid):
    conn = None
    try:
        data = request.get_json()
        fields = []
        vals = []
        allowed = ["estado", "fecha_planificada", "fecha_real", "observaciones"]
        for k in allowed:
            if k in data:
                val = data[k]
                if val == "": val = None
                # FIX: Cast fecha_real a DATE al guardar para evitar offset de timezone
                if k == "fecha_real" and val is not None:
                    fields.append(f"{k} = %s::date")
                else:
                    fields.append(f"{k} = %s")
                vals.append(val)
        
        if not fields: return jsonify({"message": "Sin datos"}), 400
        
        vals.append(current_user_id)
        vals.append(wid)
        sql = f"UPDATE licitacion_workflow SET {', '.join(fields)}, usuario_id = %s, actualizado_en = NOW() WHERE id = %s"
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(vals))
            cur.execute("UPDATE licitaciones SET fecha_actualizacion = NOW() WHERE id = (SELECT licitacion_id FROM licitacion_workflow WHERE id = %s)", (wid,))
        conn.commit()
        return jsonify({"message": "Paso actualizado"})
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error update_licitacion_workflow: {e}")
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/documentos", methods=["POST"])
@session_required
def upload_licitacion_doc(current_user_id):
    conn = None
    try:
        workflow_id = request.form.get("workflow_id")
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion", "")
        if 'archivo' not in request.files: return jsonify({"message": "Sin archivo"}), 400
        f = request.files['archivo']
        if f.filename == '': return jsonify({"message": "Nombre vacío"}), 400
        if f and allowed_file(f.filename):
            ts = int(time.time())
            ext = f.filename.rsplit('.', 1)[1].lower()
            fname = secure_filename(f"lic_{workflow_id}_{ts}.{ext}")
            target_dir = os.path.join(DOCS_FOLDER, "licitaciones")
            os.makedirs(target_dir, exist_ok=True)
            fpath = os.path.join(target_dir, fname)
            f.save(fpath)
            url = f"/api/licitaciones/docs/{fname}"
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO licitaciones_documentos 
                    (workflow_id, nombre, descripcion, url, archivo_nombre, archivo_extension, archivo_size, usuario_subida)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (workflow_id, nombre, descripcion, url, f.filename, ext, os.path.getsize(fpath), current_user_id))
            conn.commit()
            return jsonify({"message": "Documento subido", "url": url})
        return jsonify({"message": "Tipo de archivo no permitido"}), 400
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error upload_licitacion_doc: {e}")
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/licitaciones/docs/<filename>")
def serve_licitacion_doc(filename):
    target_dir = os.path.join(DOCS_FOLDER, "licitaciones")
    return send_from_directory(target_dir, filename)

@app.route("/licitaciones/biblioteca", methods=["POST"])
@session_required
def upload_biblioteca_doc(current_user_id):
    conn = None
    try:
        nombre = request.form.get("nombre")
        tipo = request.form.get("tipo", "General")
        descripcion = request.form.get("descripcion", "")
        if 'archivo' not in request.files: return jsonify({"message": "Sin archivo"}), 400
        f = request.files['archivo']
        if f.filename == '': return jsonify({"message": "Nombre vacío"}), 400
        if f and allowed_file(f.filename):
            ts = int(time.time())
            ext = f.filename.rsplit('.', 1)[1].lower()
            fname = secure_filename(f"lib_{ts}_{f.filename}")
            target_dir = os.path.join(DOCS_FOLDER, "licitaciones", "biblioteca")
            os.makedirs(target_dir, exist_ok=True)
            fpath = os.path.join(target_dir, fname)
            f.save(fpath)
            url = f"/api/licitaciones/lib/{fname}"
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO licitaciones_biblioteca 
                    (nombre, tipo, descripcion, url, archivo_nombre, archivo_extension, archivo_size, usuario_subida)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (nombre, tipo, descripcion, url, f.filename, ext, os.path.getsize(fpath), current_user_id))
            conn.commit()
            return jsonify({"message": "Documento añadido a biblioteca", "url": url})
        return jsonify({"message": "Tipo de archivo no permitido"}), 400
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error upload_biblioteca_doc: {e}")
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/biblioteca", methods=["GET"])
@session_required
def get_biblioteca_docs(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM licitaciones_biblioteca ORDER BY fecha_subida DESC")
            return jsonify(cur.fetchall())
    except Exception as e:
        logger.error(f"Error get_biblioteca_docs: {e}")
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/<int:lid>/cerrar", methods=["PUT"])
@session_required
def cerrar_licitacion(current_user_id, lid):
    """Cierra una licitación. Impide modificaciones posteriores."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE licitaciones 
                SET estado_licitacion = 'Cerrada', fecha_actualizacion = NOW()
                WHERE id = %s AND COALESCE(estado_licitacion, 'Abierta') = 'Abierta'
            """, (lid,))
            if cur.rowcount == 0:
                return jsonify({"message": "Licitación no encontrada o ya se encuentra cerrada"}), 404
            
            log_auditoria(current_user_id, "cerrar_licitacion", f"Cerró licitación {lid}")
        conn.commit()
        return jsonify({"message": "Licitación cerrada exitosamente"})
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error cerrar_licitacion: {e}")
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/<int:lid>/reabrir", methods=["PUT"])
@session_required
def reabrir_licitacion(current_user_id, lid):
    """Reabre una licitación cerrada, validando que no haya otra abierta para el mismo proyecto."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Obtener proyecto_id de la licitación
            cur.execute("SELECT proyecto_id FROM licitaciones WHERE id = %s", (lid,))
            row = cur.fetchone()
            if not row:
                return jsonify({"message": "Licitación no encontrada"}), 404
            
            proyecto_id = row[0]
            # Validar que no exista otra abierta
            cur.execute("""
                SELECT id FROM licitaciones 
                WHERE proyecto_id = %s AND COALESCE(estado_licitacion, 'Abierta') = 'Abierta' AND id != %s
            """, (proyecto_id, lid))
            if cur.fetchone():
                return jsonify({"message": "Ya existe otra licitación abierta para este proyecto. Ciérrela primero."}), 409
            
            cur.execute("""
                UPDATE licitaciones 
                SET estado_licitacion = 'Abierta', fecha_actualizacion = NOW()
                WHERE id = %s AND estado_licitacion = 'Cerrada'
            """, (lid,))
            if cur.rowcount == 0:
                return jsonify({"message": "La licitación no está cerrada o no existe"}), 400
            
            log_auditoria(current_user_id, "reabrir_licitacion", f"Reabrió licitación {lid}")
        conn.commit()
        return jsonify({"message": "Licitación reabierta exitosamente"})
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error reabrir_licitacion: {e}")
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/licitaciones/calendario", methods=["GET"])
@session_required
def get_licitaciones_calendario(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    w.id as workflow_id,
                    w.fecha_planificada::text as fecha_planificada,
                    w.fecha_real::date::text as fecha_real,
                    w.estado,
                    l.id as licitacion_id,
                    l.nombre_licitacion,
                    l.id_mercado_publico,
                    COALESCE(l.estado_licitacion, 'Abierta') as estado_licitacion,
                    p.nombre as proyecto_nombre,
                    m.nombre as paso_nombre,
                    m.orden as paso_orden
                FROM licitacion_workflow w
                JOIN licitaciones l ON l.id = w.licitacion_id
                JOIN proyectos p ON p.id = l.proyecto_id
                JOIN licitacion_pasos_maestro m ON m.id_paso = w.paso_id
                WHERE (w.fecha_planificada IS NOT NULL OR w.fecha_real IS NOT NULL)
                ORDER BY COALESCE(w.fecha_real, w.fecha_planificada)
            """)
            return jsonify(cur.fetchall())
    except Exception as e:
        logger.error(f"Error get_licitaciones_calendario: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/licitaciones/lib/<filename>")
def serve_biblioteca_doc(filename):
    target_dir = os.path.join(DOCS_FOLDER, "licitaciones", "biblioteca")
    return send_from_directory(target_dir, filename)

@app.route("/proyectos/<int:pid>", methods=["PUT"])
@session_required
def update_proyecto(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()

        forbidden = {"id", "user_id", "actualizado_por", "fecha_actualizacion"}
        data = {k: v for k, v in data.items() if k not in forbidden}

        data["actualizado_por"] = current_user_id

        fields = []
        values = []

        for k, v in data.items():
            fields.append(f"{k} = %s")
            values.append(v)

        fields.append("fecha_actualizacion = NOW()")

        sql = f"""
            UPDATE proyectos
            SET {', '.join(fields)}
            WHERE id = %s
        """

        values.append(pid)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(values))

        conn.commit()
        
        log_control(current_user_id, "editar_proyecto", modulo="proyectos", 
                    entidad_tipo="proyecto", entidad_id=pid,
                    detalle="Actualización de datos del proyecto")

        return jsonify({"message": "Proyecto actualizado"})

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos/<int:pid>", methods=["DELETE"])
@session_required
def delete_proyecto(current_user_id, pid):
    conn = None
    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE proyectos
                SET activo = FALSE,
                    actualizado_por = %s,
                    fecha_actualizacion = NOW()
                WHERE id = %s
                  AND activo = TRUE
            """, (current_user_id, pid))

            if cur.rowcount == 0:
                return jsonify({
                    "message": "Proyecto no encontrado o ya desactivado"
                }), 404

        conn.commit()

        log_control(current_user_id, "eliminar_proyecto", modulo="proyectos",
                    entidad_tipo="proyecto", entidad_id=pid,
                    detalle="Desactivación lógica del proyecto (activo=false)")

        return jsonify({
            "message": "Proyecto desactivado"
        })

    finally:
        if conn:
            release_db_connection(conn)


def crud_simple(tabla, current_user_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"SELECT * FROM {tabla}")
        rows = cur.fetchall()
    release_db_connection(conn)
    return jsonify(rows)

# Función auxiliar para Crear (POST)
def generic_create(table_name, data, extra_columns=None):
    if extra_columns is None:
        extra_columns = []

    # Lista de columnas: nombre + las extras
    columns = ["nombre"] + extra_columns
    # Valores correspondientes
    values = [data.get("nombre")] + [data.get(col) for col in extra_columns]
    # Placeholders para SQL seguro (%s)
    placeholders = ", ".join(["%s"] * len(columns))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({placeholders})
                RETURNING id
            """
            cur.execute(query, values)
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    finally:
        release_db_connection(conn)

# Función auxiliar para Actualizar (PUT)
def generic_update(table_name, id, data, extra_columns=None):
    if extra_columns is None:
        extra_columns = []

    # Siempre actualizamos nombre y activo
    set_clauses = ["nombre = %s", "activo = %s"]
    # Valores iniciales
    values = [data.get("nombre"), data.get("activo", True)]

    # Agregamos columnas extra dinámicamente
    for col in extra_columns:
        set_clauses.append(f"{col} = %s")
        values.append(data.get(col))

    # Agregamos el ID para el WHERE
    values.append(id)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = f"""
                UPDATE {table_name}
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            cur.execute(query, values)
        conn.commit()
    finally:
        release_db_connection(conn)

# Función auxiliar para Eliminar (DELETE - Soft Delete)
def generic_delete(table_name, id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {table_name} SET activo = FALSE WHERE id = %s", (id,))
        conn.commit()
    finally:
        release_db_connection(conn)

@app.route("/areas", methods=["GET"])
@session_required
def get_areas(current_user_id):
    return crud_simple("areas", current_user_id)

@app.route("/areas", methods=["POST"])
@session_required
def create_area(current_user_id):
    data = request.get_json()
    conn = get_db_connection()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO areas (nombre) VALUES (%s) RETURNING id",
            (data["nombre"],)
        )
        new_id = cur.fetchone()[0]

    conn.commit()
    release_db_connection(conn)

    return jsonify({"id": new_id}), 201

@app.route("/areas/<int:id>", methods=["PUT"])
@session_required
def update_area(current_user_id, id):
    data = request.get_json()
    conn = get_db_connection()

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE areas
            SET nombre = %s,
                activo = %s
            WHERE id = %s
        """, (
            data.get("nombre"),
            data.get("activo", True),
            id
        ))

    conn.commit()
    release_db_connection(conn)

    return jsonify({"message": "Actualizado"})

@app.route("/areas/<int:id>", methods=["DELETE"])
@session_required
def delete_area(current_user_id, id):
    conn = None
    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE areas
                SET activo = FALSE
                WHERE id = %s
            """, (id,))

        conn.commit()

        return jsonify({
            "message": "Área desactivada"
        })

    finally:
        if conn:
            release_db_connection(conn)

# --- Financiamientos ---
@app.route("/financiamientos", methods=["GET"])
@session_required
def get_financiamientos(current_user_id):
    return crud_simple("financiamientos", current_user_id)

@app.route("/financiamientos", methods=["POST"])
@session_required
def create_financiamiento(current_user_id):
    data = request.get_json()
    new_id = generic_create("financiamientos", data)
    return jsonify({"id": new_id}), 201

@app.route("/financiamientos/<int:id>", methods=["PUT"])
@session_required
def update_financiamiento(current_user_id, id):
    data = request.get_json()
    generic_update("financiamientos", id, data)
    return jsonify({"message": "Actualizado"})

@app.route("/financiamientos/<int:id>", methods=["DELETE"])
@session_required
def delete_financiamiento(current_user_id, id):
    generic_delete("financiamientos", id)
    return jsonify({"message": "Financiamiento desactivado"})


# --- Estados Postulación ---
@app.route("/estados_postulacion", methods=["GET"])
@session_required
def get_estados_postulacion(current_user_id):
    return crud_simple("estados_postulacion", current_user_id)

@app.route("/estados_postulacion", methods=["POST"])
@session_required
def create_estado_postulacion(current_user_id):
    data = request.get_json()
    new_id = generic_create("estados_postulacion", data)
    return jsonify({"id": new_id}), 201

@app.route("/estados_postulacion/<int:id>", methods=["PUT"])
@session_required
def update_estado_postulacion(current_user_id, id):
    data = request.get_json()
    generic_update("estados_postulacion", id, data)
    return jsonify({"message": "Actualizado"})

@app.route("/estados_postulacion/<int:id>", methods=["DELETE"])
@session_required
def delete_estado_postulacion(current_user_id, id):
    generic_delete("estados_postulacion", id)
    return jsonify({"message": "Estado desactivado"})


# --- Sectores ---
@app.route("/sectores", methods=["GET"])
@session_required
def get_sectores(current_user_id):
    return crud_simple("sectores", current_user_id)

@app.route("/sectores", methods=["POST"])
@session_required
def create_sector(current_user_id):
    data = request.get_json()
    new_id = generic_create("sectores", data)
    return jsonify({"id": new_id}), 201

@app.route("/sectores/<int:id>", methods=["PUT"])
@session_required
def update_sector(current_user_id, id):
    data = request.get_json()
    generic_update("sectores", id, data)
    return jsonify({"message": "Actualizado"})

@app.route("/sectores/<int:id>", methods=["DELETE"])
@session_required
def delete_sector(current_user_id, id):
    generic_delete("sectores", id)
    return jsonify({"message": "Sector desactivado"})


# --- Lineamientos Estratégicos ---
@app.route("/lineamientos_estrategicos", methods=["GET"])
@session_required
def get_lineamientos(current_user_id):
    return crud_simple("lineamientos_estrategicos", current_user_id)

@app.route("/lineamientos_estrategicos", methods=["POST"])
@session_required
def create_lineamiento(current_user_id):
    data = request.get_json()
    new_id = generic_create("lineamientos_estrategicos", data)
    return jsonify({"id": new_id}), 201

@app.route("/lineamientos_estrategicos/<int:id>", methods=["PUT"])
@session_required
def update_lineamiento(current_user_id, id):
    data = request.get_json()
    generic_update("lineamientos_estrategicos", id, data)
    return jsonify({"message": "Actualizado"})

@app.route("/lineamientos_estrategicos/<int:id>", methods=["DELETE"])
@session_required
def delete_lineamiento(current_user_id, id):
    generic_delete("lineamientos_estrategicos", id)
    return jsonify({"message": "Lineamiento desactivado"})

# --- Etapas Proyecto (Tiene 'orden') ---
@app.route("/etapas_proyecto", methods=["GET"])
@session_required
def get_etapas_proyecto(current_user_id):
    return crud_simple("etapas_proyecto", current_user_id)

@app.route("/etapas_proyecto", methods=["POST"])
@session_required
def create_etapa_proyecto(current_user_id):
    data = request.get_json()
    # Pasamos ['orden'] como lista de columnas extra
    new_id = generic_create("etapas_proyecto", data, extra_columns=['orden'])
    return jsonify({"id": new_id}), 201

@app.route("/etapas_proyecto/<int:id>", methods=["PUT"])
@session_required
def update_etapa_proyecto(current_user_id, id):
    data = request.get_json()
    generic_update("etapas_proyecto", id, data, extra_columns=['orden'])
    return jsonify({"message": "Actualizado"})

@app.route("/etapas_proyecto/<int:id>", methods=["DELETE"])
@session_required
def delete_etapa_proyecto(current_user_id, id):
    generic_delete("etapas_proyecto", id)
    return jsonify({"message": "Etapa desactivada"})


# --- Estados Proyecto (Tiene 'orden' y 'color') ---
@app.route("/estados_proyecto", methods=["GET"])
@session_required
def get_estados_proyecto(current_user_id):
    return crud_simple("estados_proyecto", current_user_id)

@app.route("/estados_proyecto", methods=["POST"])
@session_required
def create_estado_proyecto(current_user_id):
    data = request.get_json()
    # Pasamos ['orden', 'color'] como columnas extra
    new_id = generic_create("estados_proyecto", data, extra_columns=['orden', 'color'])
    return jsonify({"id": new_id}), 201

@app.route("/estados_proyecto/<int:id>", methods=["PUT"])
@session_required
def update_estado_proyecto(current_user_id, id):
    data = request.get_json()
    generic_update("estados_proyecto", id, data, extra_columns=['orden', 'color'])
    return jsonify({"message": "Actualizado"})

@app.route("/estados_proyecto/<int:id>", methods=["DELETE"])
@session_required
def delete_estado_proyecto(current_user_id, id):
    generic_delete("estados_proyecto", id)
    return jsonify({"message": "Estado desactivado"})



# DOCUMENTOS
@app.route("/proyectos/<int:pid>/documentos", methods=["POST"])
@session_required
def add_doc(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()
        if not data or "nombre_archivo" not in data or "url_archivo" not in data:
            return jsonify({"message": "Datos incompletos"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documentos (proyecto_id, nombre_archivo, url_archivo)
                VALUES (%s, %s, %s) RETURNING doc_id
            """, (pid, data["nombre_archivo"], data["url_archivo"]))
            doc_id = cur.fetchone()[0]
        conn.commit()

        log_auditoria(current_user_id, "add_documento", f"Agregó doc_id={doc_id} al proyecto {pid}")

        return jsonify({"message": "Documento agregado", "doc_id": doc_id}), 201
    except Exception as e:
        logger.error(f"Error en add_doc: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route("/mapas/por-rol/<int:role_id>", methods=["GET"])
@session_required
def get_mapas_by_role(current_user_id, role_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT
                    m.mapa_id,
                    m.nombre,
                    m.descripcion
                FROM mapas m
                INNER JOIN mapas_roles mr ON mr.mapa_id = m.mapa_id
                WHERE mr.role_id = %s
            """, (role_id,))

            mapas = cur.fetchall()

        return jsonify({
            "role_id": role_id,
            "mapas": mapas
        })

    except Exception as e:
        logger.error(f"Error en get_mapas_by_role: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos/<int:pid>/documentos/upload", methods=["POST"])
@session_required
def upload_documento(current_user_id, pid):
#def upload_documento(pid):
    conn = None
    try:
        if "file" not in request.files:
            return jsonify({"message": "Archivo no enviado"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"message": "Nombre de archivo vacío"}), 400

        if not allowed_file(file.filename):
            return jsonify({"message": "Tipo de archivo no permitido"}), 400

        # Datos opcionales
        tipo_documento = request.form.get("tipo_documento")
        descripcion = request.form.get("descripcion")

        filename = secure_filename(file.filename)
        extension = filename.rsplit(".", 1)[1].lower()

        # Crear carpeta por proyecto
        proyecto_dir = os.path.join(DOCS_FOLDER, str(pid))
        os.makedirs(proyecto_dir, exist_ok=True)

        # Nombre único
        unique_name = f"{int(time.time())}_{filename}"
        file_path = os.path.join(proyecto_dir, unique_name)

        # Guardar archivo
        file.save(file_path)

        file_size = os.path.getsize(file_path)

        # URL local (ajusta si usas nginx o reverse proxy)
        file_url = f"/docs/{pid}/{unique_name}"

        # Guardar en BD
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proyectos_documentos (
                    proyecto_id,
                    tipo_documento,
                    nombre,
                    descripcion,
                    url,
                    archivo_nombre,
                    archivo_extension,
                    archivo_size
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING documento_id
            """, (
                pid,
                tipo_documento,
                filename,
                descripcion,
                file_url,
                unique_name,
                extension,
                file_size
            ))

            documento_id = cur.fetchone()[0]

            # Actualizar fecha del proyecto
            cur.execute("UPDATE proyectos SET fecha_actualizacion = NOW() WHERE id = %s", (pid,))

        conn.commit()

        log_auditoria(
            current_user_id,
            #1,
            "upload_documento",
            f"Subió documento {documento_id} al proyecto {pid}"
        )

        return jsonify({
            "message": "Documento subido correctamente",
            "documento_id": documento_id,
            "url": file_url
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error en upload_documento: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno", "detail": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos/<int:pid>/documentos", methods=["GET"])
#@session_required
#def listar_documentos_proyecto(current_user_id, pid):
def listar_documentos_proyecto(pid): 
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            #ORDER BY fecha_subida DESC
            cur.execute("""
                SELECT
                    documento_id,
                    proyecto_id,
                    tipo_documento,
                    nombre,
                    descripcion,
                    url,
                    archivo_nombre,
                    archivo_extension,
                    archivo_size,
                    fecha_subida
                FROM proyectos_documentos
                WHERE proyecto_id = %s
                
            """, (pid,))

            documentos = cur.fetchall()

        return jsonify({
            "proyecto_id": pid,
            "total": len(documentos),
            "documentos": documentos
        })

    except Exception as e:
        logger.error(f"Error listando documentos proyecto {pid}: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)



@app.route("/proyectos/<int:pid>/documentos/descargar", methods=["GET"])
@session_required
def descargar_documentos_proyecto(current_user_id, pid):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT archivo_nombre
                FROM proyectos_documentos
                WHERE proyecto_id = %s
            """, (pid,))
            archivos = cur.fetchall()

        if not archivos:
            return jsonify({"message": "El proyecto no tiene documentos"}), 404

        proyecto_dir = os.path.join(DOCS_FOLDER, str(pid))
        if not os.path.exists(proyecto_dir):
            return jsonify({"message": "Carpeta de documentos no encontrada"}), 404

        # ZIP en memoria
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for a in archivos:
                file_path = os.path.join(proyecto_dir, a["archivo_nombre"])
                if os.path.exists(file_path):
                    zipf.write(
                        file_path,
                        arcname=a["archivo_nombre"]
                    )

        zip_buffer.seek(0)

        log_auditoria(
            current_user_id,
            "download_documentos",
            f"Descargó documentos del proyecto {pid}"
        )

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"proyecto_{pid}_documentos.zip"
        )

    except Exception as e:
        logger.error(f"Error descargando documentos proyecto {pid}: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route("/documentos", methods=["GET"])
@session_required
def get_all_documentos(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    d.documento_id,
                    d.proyecto_id,
                    p.nombre as proyecto_nombre,
                    d.tipo_documento,
                    d.nombre,
                    d.descripcion,
                    d.url,
                    d.archivo_nombre,
                    d.archivo_extension,
                    d.archivo_size,
                    d.fecha_subida
                FROM proyectos_documentos d
                LEFT JOIN proyectos p ON p.id = d.proyecto_id
                ORDER BY d.fecha_subida DESC
            """)
            documentos = cur.fetchall()

        return jsonify(documentos)

    except Exception as e:
        logger.error(f"Error listando todos los documentos: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route("/documentos/<int:documento_id>", methods=["GET"])
@session_required
def get_documento_metadata(current_user_id, documento_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    documento_id,
                    proyecto_id,
                    tipo_documento,
                    nombre,
                    descripcion,
                    archivo_extension,
                    archivo_size,
                    fecha_subida
                FROM proyectos_documentos
                WHERE documento_id = %s
            """, (documento_id,))
            doc = cur.fetchone()

        if not doc:
            return jsonify({"message": "Documento no encontrado"}), 404

        return jsonify(doc)

    except Exception as e:
        logger.error(f"Error get_documento_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/documentos/<int:documento_id>/view", methods=["GET"])
@session_required
def view_documento(current_user_id, documento_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    proyecto_id,
                    archivo_nombre,
                    archivo_extension,
                    nombre
                FROM proyectos_documentos
                WHERE documento_id = %s
            """, (documento_id,))
            doc = cur.fetchone()

        if not doc:
            return jsonify({"message": "Documento no encontrado"}), 404

        file_path = os.path.join(
            DOCS_FOLDER,
            str(doc["proyecto_id"]),
            doc["archivo_nombre"]
        )

        if not os.path.exists(file_path):
            return jsonify({"message": "Archivo no existe en disco"}), 404

        # MIME type básico
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg"
        }

        mimetype = mime_map.get(
            doc["archivo_extension"].lower(),
            "application/octet-stream"
        )

        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=False,  # 👈 clave para visualizar
            download_name=doc["nombre"]
        )

    except Exception as e:
        logger.error(f"Error view_documento: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

def get_texto_documentos_proyecto(proyecto_id):
    conn = None
    textos = []

    try:
        conn = get_db_connection()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT archivo_nombre, archivo_extension
                FROM proyectos_documentos
                WHERE proyecto_id = %s
            """, (proyecto_id,))

            documentos = cur.fetchall()

        proyecto_dir = os.path.join(DOCS_FOLDER, str(proyecto_id))

        for doc in documentos:
            ext = doc["archivo_extension"].lower()

            if ext not in ALLOWED_EXTENSIONS:
                continue

            file_path = os.path.join(proyecto_dir, doc["archivo_nombre"])

            if not os.path.exists(file_path):
                continue

            texto = extract_text_from_file(file_path, ext)

            if texto.strip():
                textos.append(
                    f"\n--- Documento: {doc['archivo_nombre']} ---\n{texto}"
                )

        return "\n".join(textos)

    except Exception as e:
        logger.error(f"Error leyendo documentos proyecto {proyecto_id}: {e}")
        return ""

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos/<int:pid>/documentos/texto", methods=["GET"])
@session_required
def obtener_texto_documentos(current_user_id, pid):
    texto = get_texto_documentos_proyecto(pid)

    return jsonify({
        "proyecto_id": pid,
        "texto": texto,
        "chars": len(texto)
    })


# GEOMAPAS
@app.route("/proyectos/<int:pid>/geomapas", methods=["POST"])
@session_required
def crear_geomapa(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()

        if not data or "geojson" not in data:
            return jsonify({"message": "GeoJSON requerido"}), 400

        nombre = data.get("nombre")
        descripcion = data.get("descripcion")
        geojson = data["geojson"]

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proyectos_geomapas (
                    proyecto_id,
                    nombre,
                    descripcion,
                    geojson
                )
                VALUES (%s, %s, %s, %s::jsonb)
                RETURNING geomapa_id
            """, (
                pid,
                nombre,
                descripcion,
                json.dumps(geojson)
            ))

            geomapa_id = cur.fetchone()[0]

        conn.commit()

        log_auditoria(
            current_user_id,
            "crear_geomapa",
            f"Creó geomapa {geomapa_id} en proyecto {pid}"
        )

        return jsonify({
            "message": "Geomapa creado correctamente",
            "geomapa_id": geomapa_id
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error crear_geomapa: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos/<int:pid>/geomapas", methods=["GET"])
def listar_geomapas_proyecto(pid):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            #ORDER BY fecha_creacion DESC
            cur.execute("""
                SELECT
                    geomapa_id,
                    proyecto_id,
                    nombre,
                    descripcion,
                    fecha_creacion
                FROM proyectos_geomapas
                WHERE proyecto_id = %s                
            """, (pid,))

            geomapas = cur.fetchall()

        return jsonify({
            "proyecto_id": pid,
            "total": len(geomapas),
            "geomapas": geomapas
        })

    except Exception as e:
        logger.error(f"Error listando geomapas proyecto {pid}: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/geomapas/<int:geomapa_id>", methods=["GET"])
@session_required
def get_geomapa_metadata(current_user_id, geomapa_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    geomapa_id,
                    proyecto_id,
                    nombre,
                    descripcion,
                    fecha_creacion
                FROM proyectos_geomapas
                WHERE geomapa_id = %s
            """, (geomapa_id,))

            geomapa = cur.fetchone()

        if not geomapa:
            return jsonify({"message": "Geomapa no encontrado"}), 404

        return jsonify(geomapa)

    except Exception as e:
        logger.error(f"Error get_geomapa_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/geomapas/<int:geomapa_id>/geojson", methods=["GET"])
@session_required
def view_geomapa_geojson(current_user_id, geomapa_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    geojson
                FROM proyectos_geomapas
                WHERE geomapa_id = %s
            """, (geomapa_id,))

            result = cur.fetchone()

        if not result:
            return jsonify({"message": "Geomapa no encontrado"}), 404

        log_auditoria(
            current_user_id,
            "view_geomapa",
            f"Visualizó geomapa {geomapa_id}"
        )

        return jsonify(result["geojson"])

    except Exception as e:
        logger.error(f"Error view_geomapa_geojson: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)


# Hitos
@app.route("/proyectos/<int:pid>/hitos", methods=["POST"])
@session_required
def create_proyecto_hito(current_user_id, pid):
    data = request.get_json()

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO proyectos_hitos (
                proyecto_id,
                fecha,
                observacion,
                categoria_hito,
                creado_por
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            pid,
            data["fecha"],
            data.get("observacion"),
            data.get("categoria_hito"),
            current_user_id
        ))
        hito_id = cur.fetchone()[0]

        # Actualizar fecha del proyecto
        cur.execute("UPDATE proyectos SET fecha_actualizacion = NOW() WHERE id = %s", (pid,))

    conn.commit()
    release_db_connection(conn)

    return jsonify({"id": hito_id}), 201


@app.route("/proyectos/<int:pid>/hitos", methods=["GET"])
@session_required
def get_proyecto_hitos(current_user_id, pid):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                h.*,
                hc.nombre AS categoria_nombre
            FROM proyectos_hitos h
            LEFT JOIN hitoscalendario hc ON hc.id = h.categoria_hito
            WHERE h.proyecto_id = %s
            ORDER BY h.fecha
        """, (pid,))
        rows = cur.fetchall()

    release_db_connection(conn)
    return jsonify(rows)

@app.route("/hitos/<int:hito_id>", methods=["GET"])
@session_required
def get_hito_metadata(current_user_id, hito_id):
    conn = None
    try:
        conn = get_db_connection()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    proyecto_id,
                    fecha,
                    observacion,
                    creado_por,
                    creado_en
                FROM proyectos_hitos
                WHERE id = %s
            """, (hito_id,))

            hito = cur.fetchone()

        if not hito:
            return jsonify({"message": "Hito no encontrado"}), 404

        return jsonify(hito)

    except Exception as e:
        logger.error(f"Error get_hito_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/hitos/<int:hito_id>/detalle", methods=["GET"])
@session_required
def view_hito_detalle(current_user_id, hito_id):
    conn = None
    try:
        conn = get_db_connection()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    fecha,
                    observacion,
                    creado_por
                FROM proyectos_hitos
                WHERE id = %s
            """, (hito_id,))

            hito = cur.fetchone()

        if not hito:
            return jsonify({"message": "Hito no encontrado"}), 404

        log_auditoria(
            current_user_id,
            "view_hito",
            f"Visualizó hito {hito_id}"
        )

        return jsonify(hito)

    except Exception as e:
        logger.error(f"Error view_hito_detalle: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# OBSERVACION
@app.route("/proyectos/<int:pid>/observaciones", methods=["POST"])
@session_required
def crear_observacion(current_user_id, pid):
    conn = None
    try:
        data = request.get_json()

        if not data or "fecha" not in data:
            return jsonify({"message": "fecha es requerida"}), 400

        fecha = data["fecha"]
        observacion = data.get("observacion")

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proyectos_observaciones (
                    proyecto_id,
                    fecha,
                    observacion,
                    creado_por
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                pid,
                fecha,
                observacion,
                current_user_id
            ))

            observacion_id = cur.fetchone()[0]

        conn.commit()

        log_auditoria(
            current_user_id,
            "crear_observacion",
            f"Creó observación {observacion_id} en proyecto {pid}"
        )

        return jsonify({
            "message": "Observación creada correctamente",
            "observacion_id": observacion_id
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error crear_observacion: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/proyectos/<int:pid>/observaciones", methods=["GET"])
def listar_observaciones_proyecto(pid):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conexión BD"}), 500

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            #ORDER BY fecha ASC, creado_en ASC
            cur.execute("""
                SELECT
                    id,
                    proyecto_id,
                    fecha,
                    observacion,
                    creado_por,
                    creado_en
                FROM proyectos_observaciones
                WHERE proyecto_id = %s                
            """, (pid,))

            observaciones = cur.fetchall()

        return jsonify({
            "proyecto_id": pid,
            "total": len(observaciones),
            "observaciones": observaciones
        })

    except Exception as e:
        logger.error(f"Error listando observaciones proyecto {pid}: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/observaciones/<int:observacion_id>", methods=["GET"])
@session_required
def get_observacion_metadata(current_user_id, observacion_id):
    conn = None
    try:
        conn = get_db_connection()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    proyecto_id,
                    fecha,
                    observacion,
                    creado_por,
                    creado_en
                FROM proyectos_observaciones
                WHERE id = %s
            """, (observacion_id,))

            observacion = cur.fetchone()

        if not observacion:
            return jsonify({"message": "Observación no encontrada"}), 404

        return jsonify(observacion)

    except Exception as e:
        logger.error(f"Error get_observacion_metadata: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/observaciones/<int:observacion_id>/detalle", methods=["GET"])
@session_required
def view_observacion_detalle(current_user_id, observacion_id):
    conn = None
    try:
        conn = get_db_connection()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    fecha,
                    observacion,
                    creado_por
                FROM proyectos_observaciones
                WHERE id = %s
            """, (observacion_id,))

            observacion = cur.fetchone()

        if not observacion:
            return jsonify({"message": "Observación no encontrada"}), 404

        log_auditoria(
            current_user_id,
            "view_observacion",
            f"Visualizó observación {observacion_id}"
        )

        return jsonify(observacion)

    except Exception as e:
        logger.error(f"Error view_observacion_detalle: {e}")
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route("/calendario_eventos", methods=["POST"])
@session_required
def create_calendario_evento(current_user_id):
    data = request.get_json()

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO calendario_eventos (
                titulo,
                descripcion,
                fecha_inicio,
                fecha_termino,
                todo_el_dia,
                categoria_calendario,
                origen_tipo,
                origen_id,
                ubicacion,
                creado_por
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            data["titulo"],
            data.get("descripcion"),
            data["fecha_inicio"],
            data.get("fecha_termino"),
            data.get("todo_el_dia", True),
            data.get("categoria_calendario"),
            data.get("origen_tipo"),
            data.get("origen_id"),
            data.get("ubicacion"),
            current_user_id
        ))
        event_id = cur.fetchone()[0]

    conn.commit()
    release_db_connection(conn)

    return jsonify({"id": event_id}), 201


@app.route("/calendario_eventos", methods=["GET"])
@session_required
def get_calendario_eventos(current_user_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                e.*,
                hc.nombre AS categoria_nombre
            FROM calendario_eventos e
            LEFT JOIN hitoscalendario hc ON hc.id = e.categoria_calendario
            WHERE e.activo = TRUE
            ORDER BY e.fecha_inicio
        """)
        rows = cur.fetchall()

    release_db_connection(conn)
    return jsonify(rows)


@app.route("/calendario_eventos/<int:evento_id>", methods=["PUT"])
@session_required
def update_calendario_evento(current_user_id, evento_id):
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Sin datos"}), 400

        allowed = {
            "titulo", "descripcion", "fecha_inicio", "fecha_termino",
            "todo_el_dia", "origen_tipo", "origen_id",
            "ubicacion", "activo"
        }

        fields = []
        values = []

        for k, v in data.items():
            if k in allowed:
                fields.append(f"{k} = %s")
                values.append(v)

        if not fields:
            return jsonify({"message": "No hay campos válidos"}), 400

        values.append(evento_id)

        sql = f"""
            UPDATE calendario_eventos
            SET {', '.join(fields)}
            WHERE id = %s
        """

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, values)

        conn.commit()

        log_auditoria(
            current_user_id,
            "update_evento",
            f"Actualizó evento calendario id={evento_id}"
        )

        return jsonify({"message": "Evento actualizado"})

    finally:
        if conn:
            release_db_connection(conn)

@app.route("/calendario_eventos/<int:evento_id>", methods=["DELETE"])
@session_required
def delete_calendario_evento(current_user_id, evento_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE calendario_eventos
                SET activo = FALSE
                WHERE id = %s AND activo = TRUE
            """, (evento_id,))

            if cur.rowcount == 0:
                return jsonify({"message": "Evento no encontrado"}), 404

        conn.commit()

        log_auditoria(
            current_user_id,
            "delete_evento",
            f"Desactivó evento calendario id={evento_id}"
        )

        return jsonify({"message": "Evento desactivado"})

    finally:
        if conn:
            release_db_connection(conn)

# hitoscalendario

@app.route("/hitoscalendario", methods=["GET"])
@session_required
def get_hitoscalendario(current_user_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, nombre, is_hito
            FROM hitoscalendario
            ORDER BY nombre
        """)
        rows = cur.fetchall()
    release_db_connection(conn)
    return jsonify(rows)

@app.route("/hitoscalendario", methods=["POST"])
@session_required
def create_hitoscalendario(current_user_id):
    data = request.get_json()

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO hitoscalendario (nombre, is_hito)
            VALUES (%s, %s)
            RETURNING id
        """, (
            data["nombre"],
            data.get("is_hito", True)
        ))
        new_id = cur.fetchone()[0]

    conn.commit()
    release_db_connection(conn)

    return jsonify({"id": new_id}), 201

@app.route("/hitoscalendario/<int:id>", methods=["PUT"])
@session_required
def update_hitoscalendario(current_user_id, id):
    data = request.get_json()

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE hitoscalendario
            SET nombre = %s,
                is_hito = %s
            WHERE id = %s
        """, (
            data["nombre"],
            data.get("is_hito", True),
            id
        ))

    conn.commit()
    release_db_connection(conn)

    return jsonify({"message": "Actualizado"})

@app.route("/hitoscalendario/<int:id>", methods=["DELETE"])
@session_required
def delete_hitoscalendario(current_user_id, id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM hitoscalendario WHERE id = %s", (id,))
    conn.commit()
    release_db_connection(conn)

    return jsonify({"message": "Eliminado"})

@app.route("/calendario_eventos_detalle", methods=["GET"])
@session_required
def get_calendario_eventos_detalle(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM vw_calendario_eventos_full
                ORDER BY fecha_inicio
            """)
            eventos = cur.fetchall()

        return jsonify(eventos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()



# AUDITORÍA
@app.route("/auditoria", methods=["GET"])
@session_required
def get_auditoria(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error conex BD"}), 500
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            #ORDER BY a.fecha DESC
            cur.execute("""
                SELECT a.audit_id, a.user_id, u.nombre AS usuario, a.accion, a.descripcion, a.fecha
                FROM auditoria a
                LEFT JOIN users u ON a.user_id = u.user_id                
                LIMIT 1000
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error en get_auditoria: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# -----------------------
# CLEANUP: Cerrar el pool de conexiones al salir
# -----------------------
@app.teardown_appcontext
def close_connection(exception=None):
    """Función que se ejecuta al final de cada petición para asegurar que las conexiones se devuelvan al pool"""
    pass  # Las conexiones se gestionan manualmente con release_db_connection

def cleanup():
    """Cierra el pool de conexiones al terminar la aplicación"""
    global connection_pool
    
    # Cerrar el pool de conexiones
    try:
        with pool_lock:
            if connection_pool and not connection_pool.closed:
                connection_pool.closeall()
                logger.info("Pool de conexiones cerrado correctamente")
    except Exception as e:
        logger.error(f"Error al cerrar el pool de conexiones: {e}")

# ============================================
# MOBILE API CONFIGURATION AND UTILITIES
# ============================================
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import timedelta
import io

# CONFIG FOTOS REPORTES
FOTOS_DIR = os.path.join(os.path.dirname(__file__), "fotos_reportes")
os.makedirs(FOTOS_DIR, exist_ok=True)

from flask import send_from_directory

@app.route('/fotos_reportes/<path:filename>')
def servir_foto_reporte(filename):
    return send_from_directory(FOTOS_DIR, filename)

# Utilidades para imágenes
def es_imagen(f): 
    return '.' in f and f.rsplit('.', 1)[1].lower() in {'png','jpg','jpeg','webp'}

def optimizar_imagen(data):
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode in ('RGBA','LA','P'):
            bg = Image.new('RGB', img.size, (255,255,255))
            bg.paste(img, mask=img.split()[-1] if img.mode=='RGBA' else None)
            img = bg
        if max(img.size) > 1920: img.thumbnail((1920,1920), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=85, optimize=True)
        return out.getvalue()
    except: return data

def extraer_gps(data):
    try:
        img = Image.open(io.BytesIO(data))
        exif = img._getexif()
        meta = {'ancho_px': img.width, 'alto_px': img.height}
        if not exif: return meta
        
        gps = {}
        for tag_id, val in exif.items():
            if TAGS.get(tag_id) == 'GPSInfo':
                for gps_id in val:
                    gps[GPSTAGS.get(gps_id, gps_id)] = val[gps_id]
        
        if 'GPSLatitude' in gps and 'GPSLongitude' in gps:
            def to_dec(coords, ref):
                d = float(coords[0]) + float(coords[1])/60 + float(coords[2])/3600
                return -d if ref in ['S','W'] else d
            meta['latitud'] = to_dec(gps['GPSLatitude'], gps.get('GPSLatitudeRef','N'))
            meta['longitud'] = to_dec(gps['GPSLongitude'], gps.get('GPSLongitudeRef','E'))
        
        dt = exif.get('DateTimeOriginal') or exif.get('DateTime')
        if dt:
            try: meta['fecha_captura'] = datetime.strptime(dt, '%Y:%m:%d %H:%M:%S')
            except: pass
        return meta
    except: return {}

# ============================================
# MOBILE API: REGISTRO (Simplificado)
# ============================================
@app.route("/api/mobile/auth/register", methods=["POST"])
def registrar():
    conn = None
    try:
        d = request.get_json()
        if not all(k in d for k in ['email','password','nombre']):
            return jsonify({"msg":"Falta email, password o nombre"}), 400
        
        email, pwd, nom = d['email'].strip().lower(), d['password'], d['nombre'].strip()
        if len(pwd) < 6: return jsonify({"msg":"Password mínimo 6 caracteres"}), 400
        
        conn = get_db_connection()
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SELECT 1 FROM users WHERE email=%s", (email,))
            if c.fetchone(): 
                return jsonify({"msg":"Email ya registrado"}), 400
        
        phash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""INSERT INTO users (email, password_hash, nombre, nivel_acceso, activo)
                        VALUES (%s, %s, %s, 0, TRUE) RETURNING user_id""",
                     (email, phash, nom))
            user_id = c.fetchone()['user_id']
            
            c.execute("SELECT role_id FROM roles WHERE nombre = 'Vecino'")
            role_row = c.fetchone()
            if role_row:
                c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                         (user_id, role_row['role_id']))
        
        conn.commit()
        return jsonify({"msg":"Registro exitoso", "user_id":user_id}), 201
        
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error registro: {e}")
        return jsonify({"msg":"Error al registrar"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# ADMIN API: CREAR FUNCIONARIO
# ============================================
@app.route("/api/admin/crear-funcionario", methods=["POST"])
@session_required
def crear_funcionario(current_user_id):
    conn = None
    try:
        d = request.get_json()
        if not all(k in d for k in ['email','password','nombre']):
            return jsonify({"msg":"Faltan datos"}), 400
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            # 1. Verificar si quien pide esto es ADMIN (nivel_acceso >= 10)
            c.execute("SELECT nivel_acceso FROM users WHERE user_id = %s", (current_user_id,))
            admin_user = c.fetchone()
            
            if not admin_user or admin_user['nivel_acceso'] < 10:
                return jsonify({"msg":"No autorizado. Se requiere nivel de acceso 10."}), 403

            # 2. Check user existe
            email, pwd, nom = d['email'].strip().lower(), d['password'], d['nombre'].strip()
            c.execute("SELECT 1 FROM users WHERE email=%s", (email,))
            if c.fetchone(): return jsonify({"msg":"Email ya registrado"}), 400
            
            # 3. Crear usuario
            phash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
            # Creamos funcionario con nivel 1 (Fiscalizador básico)
            c.execute("""INSERT INTO users (email, password_hash, nombre, nivel_acceso, activo)
                        VALUES (%s, %s, %s, 1, TRUE) RETURNING user_id""",
                     (email, phash, nom))
            new_user_id = c.fetchone()['user_id']
            
            # 4. Asignar Rol
            c.execute("SELECT role_id FROM roles WHERE nombre IN ('Fiscalizador', 'Funcionario') LIMIT 1")
            role_row = c.fetchone()
            if not role_row:
                c.execute("INSERT INTO roles (nombre) VALUES ('Fiscalizador') RETURNING role_id")
                role_row = c.fetchone()
            
            c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                     (new_user_id, role_row['role_id']))
            
            conn.commit()
            return jsonify({"msg":"Funcionario creado exitosamente", "user_id": new_user_id}), 201
            
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error crear funcionario: {e}")
        return jsonify({"msg":f"Error: {str(e)}"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MOBILE API: LOGIN (Active Sessions - NO JWT)
# ============================================
@app.route("/api/mobile/auth/login", methods=["POST"])
def login_mobile():
    conn = None
    try:
        d = request.get_json()
        email, pwd = d.get('email','').strip().lower(), d.get('password','')
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            # Consulta simplificada: Solo datos de usuario y nivel_acceso
            c.execute("""SELECT user_id, email, nombre, password_hash, activo, nivel_acceso
                        FROM users 
                        WHERE email=%s""", (email,))
            u = c.fetchone()
        
        if not u or not u['activo'] or not bcrypt.checkpw(pwd.encode(), u['password_hash'].encode()):
            return jsonify({"msg":"Credenciales inválidas"}), 401
        
        # LOGGING PARA DEBUG
        logger.info(f"LOGIN DEBUG: User {u['email']} - Nivel Acceso: {u.get('nivel_acceso')}")

        # MEJORA #4: Usar create_session con timestamp de expiración
        token = create_session(u['user_id'])
        
        # Asegurar entero
        nivel = u['nivel_acceso']
        if nivel is None: nivel = 0
        
        return jsonify({
            "token": token,
            "user": {
                "user_id": u['user_id'],
                "email": u['email'],
                "nombre": u['nombre'],
                "nivel_acceso": int(nivel),
                "roles": [] # Enviamos lista vacía para compatibilidad
            }
        }), 200
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MOBILE API: MAESTROS
# ============================================
@app.route("/api/mobile/divisiones", methods=["GET"])
def get_divisiones_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT division_id, nombre FROM divisiones ORDER BY nombre")
            rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        logger.error(f"Error divisiones: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/roles", methods=["GET"])
def get_roles_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT role_id, nombre FROM roles ORDER BY nombre")
            rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        logger.error(f"Error roles: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/estados", methods=["GET"])
def get_estados_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre FROM estados_reporte ORDER BY id")
            rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        logger.error(f"Error estados: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/gravedades", methods=["GET"])
def get_gravedades_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre FROM reportes_gravedad ORDER BY id")
            rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        logger.error(f"Error gravedades: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MOBILE API: PERFIL & ESTADÍSTICAS
# ============================================
@app.route("/api/mobile/perfil", methods=["GET"])
@session_required
def get_perfil(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            # Datos usuario
            c.execute("SELECT user_id, nombre, email, nivel_acceso FROM users WHERE user_id = %s", (current_user_id,))
            user = c.fetchone()
            
            # Estadísticas
            c.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE estado_id = 1) as pendientes, -- Reportado
                    COUNT(*) FILTER (WHERE estado_id IN (2,3)) as en_proceso, -- Verificado/Programado
                    COUNT(*) FILTER (WHERE estado_id = 4) as resueltos -- Reparado
                FROM reportes_ciudadanos 
                WHERE reportado_por = %s AND activo = TRUE
            """, (current_user_id,))
            stats = c.fetchone()
            
        return jsonify({"user": user, "stats": stats}), 200
    except Exception as e:
        logger.error(f"Error perfil: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/perfil", methods=["PUT"])
@session_required
def update_perfil(current_user_id):
    conn = None
    try:
        d = request.get_json()
        nombre = d.get('nombre')
        pwd = d.get('password')
        
        updates = []
        vals = []
        
        if nombre:
            updates.append("nombre = %s")
            vals.append(nombre)
        if pwd and len(pwd) >= 6:
            phash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
            updates.append("password_hash = %s")
            vals.append(phash)
            
        if not updates:
            return jsonify({"msg":"Nada que actualizar"}), 400
            
        vals.append(current_user_id)
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s", tuple(vals))
            conn.commit()
            
        return jsonify({"msg":"Perfil actualizado"}), 200
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error update perfil: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MOBILE API: REPORTES
# ============================================
@app.route("/api/mobile/reportes", methods=["POST"])
@session_required
def crear_reporte(current_user_id):
    conn = None
    try:
        d = request.get_json()
        required = ['categoria_id', 'latitud', 'longitud', 'direccion_referencia']
        if not all(k in d for k in required):
            return jsonify({"msg":"Faltan campos"}), 400
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""INSERT INTO reportes_ciudadanos 
                        (categoria_id, estado_id, gravedad_id, latitud, longitud, direccion_referencia, 
                         descripcion, reportado_por, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                        RETURNING id, numero_folio""",
                     (d['categoria_id'], 1, d.get('gravedad_id', 1), d['latitud'], d['longitud'], 
                      d['direccion_referencia'], d.get('descripcion'), current_user_id))
            result = c.fetchone()
        
        conn.commit()
        return jsonify({"msg":"Creado","id":result['id'],"numero_folio":result['numero_folio']}), 201
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error crear reporte: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/reportes/<int:rid>", methods=["GET"])
@session_required
def get_reporte_detalle(current_user_id, rid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT r.id, r.numero_folio, 
                        c.nombre as categoria, e.nombre as estado, g.nombre as gravedad,
                        r.categoria_id, r.estado_id, r.gravedad_id,
                        r.direccion_referencia, r.descripcion, r.revisado,
                        r.fecha_reporte, r.fecha_actualizacion, r.latitud, r.longitud,
                        u_rep.nombre as reportado_por_nombre, u_rep.email as reportado_por_email,
                        u_act.nombre as actualizado_por_nombre, u_act.email as actualizado_por_email
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
                        LEFT JOIN reportes_gravedad g ON g.id = r.gravedad_id
                        LEFT JOIN users u_rep ON u_rep.user_id = r.reportado_por
                        LEFT JOIN users u_act ON u_act.user_id = r.actualizado_por
                        WHERE r.id = %s""", (rid,))
            repo = c.fetchone()
            
        if not repo:
            return jsonify({"msg":"No encontrado"}), 404
            
        return jsonify(repo), 200
    except Exception as e:
        logger.error(f"Error detalle reporte: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/reportes/todos", methods=["GET"])
def get_todos_reportes():
    # Endpoint público para el mapa y admin
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT r.id, r.numero_folio, r.latitud, r.longitud, 
                        c.nombre as categoria, e.nombre as estado, g.nombre as gravedad,
                        r.estado_id, r.gravedad_id, r.direccion_referencia, r.categoria_id,
                        r.descripcion, r.revisado, r.fecha_reporte, r.fecha_actualizacion,
                        u_rep.nombre as reportado_por_nombre, u_rep.email as reportado_por_email,
                        u_act.nombre as actualizado_por_nombre, u_act.email as actualizado_por_email
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
                        LEFT JOIN reportes_gravedad g ON g.id = r.gravedad_id
                        LEFT JOIN users u_rep ON u_rep.user_id = r.reportado_por
                        LEFT JOIN users u_act ON u_act.user_id = r.actualizado_por
                        WHERE r.activo = TRUE
                        ORDER BY r.fecha_reporte DESC""")
            rows = c.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        logger.error(f"Error mapa: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/reportes/mis-reportes", methods=["GET"])
@session_required
def mis_reportes(current_user_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT r.id, r.numero_folio, c.nombre as categoria, e.nombre as estado,
                        r.direccion_referencia, r.descripcion, r.fecha_reporte
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
                        WHERE r.reportado_por = %s AND r.activo = TRUE
                        ORDER BY r.fecha_reporte DESC""", (current_user_id,))
            reportes = c.fetchall()
        return jsonify(reportes), 200
    except Exception as e:
        logger.error(f"Error mis reportes: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MOBILE API: AUXILIAR (Categorías)
# ============================================
@app.route("/api/mobile/categorias", methods=["GET"])
def get_categorias_mobile():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre FROM categorias_reporte ORDER BY id")
            rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        logger.error(f"Error categorias: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MOBILE API: COMENTARIOS
# ============================================
@app.route("/api/mobile/reportes/<int:rid>/comentarios", methods=["GET"])
def get_comentarios(rid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT rc.id, rc.comentario, rc.creado_en, u.nombre as autor
                        FROM reportes_comentarios rc
                        JOIN users u ON u.user_id = rc.user_id
                        WHERE rc.reporte_id = %s ORDER BY rc.creado_en""",(rid,))
            rows = c.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        logger.error(f"Error comments get: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/reportes/<int:rid>/comentarios", methods=["POST"])
@session_required
def add_comentario(current_user_id, rid):
    conn = None
    try:
        d = request.get_json()
        texto = d.get('comentario')
        if not texto: return jsonify({"msg":"Texto vacío"}), 400
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("INSERT INTO reportes_comentarios (reporte_id, user_id, comentario) VALUES (%s, %s, %s) RETURNING id",
                     (rid, current_user_id, texto))
            nid = c.fetchone()['id']
        conn.commit()
        return jsonify({"msg":"Comentario agregado","id":nid}), 201
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error comments post: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

# ============================================
# MOBILE API: ACTUALIZACIÓN ESTADO/GRAVEDAD
# ============================================
@app.route("/api/mobile/reportes/<int:rid>/actualizar", methods=["POST"])
@session_required
def actualizar_reporte(current_user_id, rid):
    conn = None
    try:
        d = request.get_json()
        
        updates = []
        vals = []
        
        if 'estado_id' in d:
            updates.append("estado_id = %s")
            vals.append(int(d['estado_id']))
        if 'gravedad_id' in d:
            updates.append("gravedad_id = %s")
            vals.append(int(d['gravedad_id']))
        if 'revisado' in d:
            updates.append("revisado = %s")
            vals.append(bool(d['revisado']))
        if 'direccion_referencia' in d:
            updates.append("direccion_referencia = %s")
            vals.append(d['direccion_referencia'])
        if 'descripcion' in d:
            updates.append("descripcion = %s")
            vals.append(d['descripcion'])
        if 'categoria_id' in d:
            updates.append("categoria_id = %s")
            vals.append(int(d['categoria_id']))
            
        if not updates:
            return jsonify({"msg":"Nada que actualizar"}), 400
        
        # Siempre actualizamos quién y cuándo modificó
        updates.append("actualizado_por = %s")
        vals.append(current_user_id)
        updates.append("fecha_actualizacion = NOW()")
        
        vals.append(rid)
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute(f"UPDATE reportes_ciudadanos SET {', '.join(updates)} WHERE id = %s RETURNING id", tuple(vals))
            result = c.fetchone()
            
            if not result:
                return jsonify({"msg":"Reporte no encontrado"}), 404
            
        conn.commit()
        return jsonify({"msg":"Reporte actualizado"}), 200
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error actualizar reporte: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

# Mantener endpoint antiguo por compatibilidad
@app.route("/api/mobile/reportes/<int:rid>/verificar", methods=["POST"])
@session_required
def verificar_reporte(current_user_id, rid):
    # Redirigir al nuevo endpoint
    return actualizar_reporte(current_user_id, rid)

# ============================================
# MOBILE API: FOTOS
# ============================================
@app.route("/api/mobile/reportes/<int:rid>/fotos", methods=["GET"])
def ver_fotos_reporte(rid):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SELECT id, ruta_archivo FROM reportes_fotos WHERE reporte_id = %s", (rid,))
            fotos = c.fetchall()
        return jsonify(fotos), 200
    except Exception as e:
        logger.error(f"Error ver fotos: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

@app.route("/api/mobile/reportes/<int:rid>/fotos", methods=["POST"])
@session_required
def subir_fotos(current_user_id, rid):
    conn = None
    try:
        logger.info(f"--- INICIO SUBIDA FOTOS REPORTE {rid} ---")
        logger.info(f"Headers: {request.headers}")
        logger.info(f"Files Keys: {request.files.keys()}")
        
        files = request.files.getlist('fotos')
        logger.info(f"Archivos encontrados con key 'fotos': {len(files)}")
        
        if not files: 
            return jsonify({"msg":"Sin fotos recibidas en backend"}), 400
        
        conn = get_db_connection()
        guardadas = []
        ym = time.strftime("%Y/%m")
        udir = os.path.join(FOTOS_DIR, ym)
        os.makedirs(udir, exist_ok=True)
        
        for i, f in enumerate(files):
            if not f: continue
            
            logger.info(f"Procesando archivo: {f.filename} ({f.content_type})")
            
            # Guardado DIRECTO sin optimización para probar
            ts = int(time.time()*1000) + i
            fname = secure_filename(f"rep_{rid}_{ts}_{f.filename}")
            fpath = os.path.join(udir, fname)
            f.save(fpath) # Guardado nativo de Flask/Werkzeug
            
            logger.info(f"Guardado en disco: {fpath}")
            
            url = f"/fotos_reportes/{ym}/{fname}"
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
                c.execute("INSERT INTO reportes_fotos (reporte_id, ruta_archivo, subido_por) VALUES (%s, %s, %s) RETURNING id",
                         (rid, url, current_user_id))
                fid = c.fetchone()['id']
            guardadas.append({"id":fid,"url":url})
        
        conn.commit()
        logger.info(f"--- FIN SUBIDA: {len(guardadas)} guardadas ---")
        return jsonify({"msg":f"{len(guardadas)} fotos subidas","fotos":guardadas}), 200
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"FATAL ERROR EN SUBIDA: {e}", exc_info=True)
        return jsonify({"msg":f"Error interno: {str(e)}"}), 500
    finally:
        if conn: release_db_connection(conn)


# ================================================================
# MÓDULO DE CONTROL – Endpoints de auditoría y trazabilidad
# ================================================================

@app.route("/control/registrar", methods=["POST"])
@session_required
def control_registrar(current_user_id):
    """
    Endpoint que el frontend llama para registrar acciones de solo-lectura
    (ver_proyecto, ver_dashboard, ver_lista, etc.) que no pasan por otros endpoints.
    """
    conn = None
    try:
        data = request.get_json() or {}
        accion        = data.get("accion", "accion_desconocida")[:80]
        modulo        = data.get("modulo", "proyectos")[:40]
        entidad_tipo  = data.get("entidad_tipo")
        entidad_id    = data.get("entidad_id")
        entidad_nombre= data.get("entidad_nombre")
        detalle       = data.get("detalle")

        log_control(
            current_user_id, accion, modulo,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            entidad_nombre=entidad_nombre,
            detalle=detalle
        )
        return jsonify({"ok": True}), 201
    except Exception as e:
        logger.error(f"Error en control_registrar: {e}")
        return jsonify({"error": str(e)}), 500



@app.route("/control/actividad", methods=["GET"])
@session_required
def control_actividad(current_user_id):
    """
    Historial completo de actividad de usuarios.
    Parámetros: user_id, accion, modulo, fecha_desde, fecha_hasta,
                entidad_tipo, entidad_id, page (default 1), per_page (default 50)
    """
    conn = None
    try:
        conn = get_db_connection()

        # Filtros opcionales
        filtros = []
        params  = []

        uid = request.args.get("user_id")
        if uid:
            filtros.append("ca.user_id = %s")
            params.append(int(uid))

        accion = request.args.get("accion")
        if accion:
            filtros.append("ca.accion ILIKE %s")
            params.append(f"%{accion}%")

        modulo = request.args.get("modulo")
        if modulo:
            filtros.append("ca.modulo = %s")
            params.append(modulo)

        fecha_desde = request.args.get("fecha_desde")
        if fecha_desde:
            filtros.append("ca.fecha >= %s")
            params.append(fecha_desde)

        fecha_hasta = request.args.get("fecha_hasta")
        if fecha_hasta:
            filtros.append("ca.fecha <= %s")
            params.append(fecha_hasta + " 23:59:59")

        entidad_tipo = request.args.get("entidad_tipo")
        if entidad_tipo:
            filtros.append("ca.entidad_tipo = %s")
            params.append(entidad_tipo)

        entidad_id = request.args.get("entidad_id")
        if entidad_id:
            filtros.append("ca.entidad_id = %s")
            params.append(int(entidad_id))

        # Búsqueda por texto libre
        q = request.args.get("q")
        if q:
            filtros.append("(ca.detalle ILIKE %s OR ca.entidad_nombre ILIKE %s OR u.nombre ILIKE %s)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]

        where_clause = ("WHERE " + " AND ".join(filtros)) if filtros else ""

        # Paginación
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(10, int(request.args.get("per_page", 50))))
        offset   = (page - 1) * per_page

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Total
            cur.execute(f"""
                SELECT COUNT(*) AS total
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                {where_clause}
            """, params)
            total = cur.fetchone()["total"]

            # Registros paginados
            cur.execute(f"""
                SELECT
                    ca.id,
                    ca.user_id,
                    u.nombre         AS nombre_usuario,
                    u.email,
                    ca.accion,
                    ca.modulo,
                    ca.entidad_tipo,
                    ca.entidad_id,
                    ca.entidad_nombre,
                    ca.exitoso,
                    ca.detalle,
                    ca.ip_origen::TEXT,
                    ca.endpoint,
                    ca.fecha
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                {where_clause}
                ORDER BY ca.fecha DESC
                LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            rows = cur.fetchall()

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "data": rows
        })
    except Exception as e:
        logger.error(f"Error en control_actividad: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)


@app.route("/control/actividad/proyecto/<int:proyecto_id>", methods=["GET"])
@session_required
def control_actividad_proyecto(current_user_id, proyecto_id):
    """Historial completo de un proyecto específico."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    ca.id, ca.accion, ca.modulo,
                    ca.user_id, u.nombre AS nombre_usuario, u.email,
                    ca.exitoso, ca.detalle,
                    ca.ip_origen::TEXT, ca.endpoint, ca.fecha
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                WHERE ca.entidad_tipo = 'proyecto' AND ca.entidad_id = %s
                ORDER BY ca.fecha DESC
                LIMIT 500
            """, (proyecto_id,))
            rows = cur.fetchall()

            # Info del proyecto
            cur.execute("SELECT id, nombre FROM proyectos WHERE id = %s", (proyecto_id,))
            proyecto = cur.fetchone()

        return jsonify({"proyecto": proyecto, "actividad": rows})
    except Exception as e:
        logger.error(f"Error en control_actividad_proyecto: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)


@app.route("/control/actividad/usuario/<int:uid>", methods=["GET"])
@session_required
def control_actividad_usuario(current_user_id, uid):
    """Historial completo de un usuario específico."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    ca.id, ca.accion, ca.modulo,
                    ca.entidad_tipo, ca.entidad_id, ca.entidad_nombre,
                    ca.exitoso, ca.detalle, ca.ip_origen::TEXT,
                    ca.endpoint, ca.fecha
                FROM control_actividad ca
                WHERE ca.user_id = %s
                ORDER BY ca.fecha DESC
                LIMIT 1000
            """, (uid,))
            actividad = cur.fetchall()

            cur.execute("""
                SELECT user_id, nombre, email, nivel_acceso
                FROM users WHERE user_id = %s
            """, (uid,))
            usuario = cur.fetchone()

        if usuario is None:
            usuario = {"user_id": uid, "nombre": f"Usuario #{uid}", "email": "", "nivel_acceso": None}

        return jsonify({"usuario": usuario, "actividad": actividad})
    except Exception as e:
        logger.error(f"Error en control_actividad_usuario: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)


@app.route("/control/kpi", methods=["GET"])
@session_required
def control_kpi(current_user_id):
    """
    KPIs globales del módulo de control:
    - total acciones, usuarios activos, proyectos accedidos
    - distribución por módulo y acción
    - actividad por día (últimos 30 días)
    - top 10 usuarios más activos
    - top 10 proyectos más visitados
    - top 5 acciones más frecuentes
    - últimas 20 acciones
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # Totales generales
            cur.execute("""
                SELECT
                    COUNT(*)                                        AS total_acciones,
                    COUNT(DISTINCT user_id)                         AS usuarios_activos,
                    COUNT(DISTINCT entidad_id)
                        FILTER (WHERE entidad_tipo = 'proyecto')    AS proyectos_accedidos,
                    COUNT(*) FILTER (WHERE exitoso = FALSE)         AS acciones_fallidas,
                    COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '24 hours') AS acciones_hoy,
                    COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '7 days')   AS acciones_semana,
                    COUNT(DISTINCT user_id) FILTER (WHERE fecha >= NOW() - INTERVAL '7 days') AS usuarios_semana
                FROM control_actividad
            """)
            totales = cur.fetchone()

            # Acciones por módulo
            cur.execute("""
                SELECT modulo, COUNT(*) AS total
                FROM control_actividad
                GROUP BY modulo ORDER BY total DESC
            """)
            por_modulo = cur.fetchall()

            # Top 10 acciones
            cur.execute("""
                SELECT accion, COUNT(*) AS total
                FROM control_actividad
                GROUP BY accion ORDER BY total DESC LIMIT 10
            """)
            top_acciones = cur.fetchall()

            # Actividad últimos 30 días (agrupada por día)
            cur.execute("""
                SELECT
                    DATE(fecha AT TIME ZONE 'America/Santiago') AS dia,
                    COUNT(*) AS total
                FROM control_actividad
                WHERE fecha >= NOW() - INTERVAL '30 days'
                GROUP BY dia ORDER BY dia ASC
            """)
            actividad_diaria = cur.fetchall()

            # Top 10 usuarios más activos
            cur.execute("""
                SELECT
                    ca.user_id, u.nombre, u.email,
                    COUNT(*) AS total_acciones,
                    MAX(ca.fecha) AS ultima_actividad
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                GROUP BY ca.user_id, u.nombre, u.email
                ORDER BY total_acciones DESC LIMIT 10
            """)
            top_usuarios = cur.fetchall()

            # Top 10 proyectos más visitados
            cur.execute("""
                SELECT
                    ca.entidad_id AS proyecto_id,
                    ca.entidad_nombre AS nombre_proyecto,
                    COUNT(*) AS total_accesos,
                    COUNT(DISTINCT ca.user_id) AS usuarios_distintos,
                    MAX(ca.fecha) AS ultimo_acceso
                FROM control_actividad ca
                WHERE ca.entidad_tipo = 'proyecto'
                  AND ca.entidad_id IS NOT NULL
                GROUP BY ca.entidad_id, ca.entidad_nombre
                ORDER BY total_accesos DESC LIMIT 10
            """)
            top_proyectos = cur.fetchall()

            # Últimas 20 acciones
            cur.execute("""
                SELECT
                    ca.id, ca.accion, ca.modulo,
                    ca.user_id, u.nombre AS nombre_usuario,
                    ca.entidad_tipo, ca.entidad_nombre,
                    ca.exitoso, ca.detalle,
                    ca.ip_origen::TEXT, ca.fecha
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                ORDER BY ca.fecha DESC LIMIT 20
            """)
            ultimas_acciones = cur.fetchall()

            # Distribución por hora del día
            cur.execute("""
                SELECT
                    EXTRACT(HOUR FROM fecha AT TIME ZONE 'America/Santiago')::INT AS hora,
                    COUNT(*) AS total
                FROM control_actividad
                WHERE fecha >= NOW() - INTERVAL '30 days'
                GROUP BY hora ORDER BY hora ASC
            """)
            por_hora = cur.fetchall()

        return jsonify({
            "totales": totales,
            "por_modulo": por_modulo,
            "top_acciones": top_acciones,
            "actividad_diaria": actividad_diaria,
            "top_usuarios": top_usuarios,
            "top_proyectos": top_proyectos,
            "ultimas_acciones": ultimas_acciones,
            "por_hora": por_hora
        })
    except Exception as e:
        logger.error(f"Error en control_kpi: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)


@app.route("/control/resumen_usuarios", methods=["GET"])
@session_required
def control_resumen_usuarios(current_user_id):
    """Tabla resumen de KPIs por usuario (desde vista materializada o cálculo directo)."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    u.user_id,
                    u.nombre AS nombre_usuario,
                    u.email,
                    u.nivel_acceso,
                    u.activo,
                    COUNT(ca.id)                                                   AS total_acciones,
                    COUNT(ca.id) FILTER (WHERE ca.accion = 'ver_proyecto')         AS vistas_proyecto,
                    COUNT(ca.id) FILTER (WHERE ca.accion = 'editar_proyecto')      AS ediciones_proyecto,
                    COUNT(ca.id) FILTER (WHERE ca.exitoso = FALSE)                 AS acciones_fallidas,
                    MAX(ca.fecha)                                                   AS ultima_actividad
                FROM users u
                LEFT JOIN control_actividad ca ON ca.user_id = u.user_id
                WHERE u.activo = TRUE
                GROUP BY u.user_id, u.nombre, u.email, u.nivel_acceso, u.activo
                ORDER BY total_acciones DESC, u.nombre ASC
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error en control_resumen_usuarios: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)


@app.route("/control/refresh_stats", methods=["POST"])
@session_required
def control_refresh_stats(current_user_id):
    """Refresca las vistas materializadas de estadísticas de control."""
    conn = None
    try:
        conn = get_db_connection()

        # Refrescar control_resumen_usuario
        try:
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY control_resumen_usuario")
            conn.commit()
        except Exception as e1:
            conn.rollback()
            logger.warning(f"CONCURRENT falló para control_resumen_usuario ({e1}), usando modo normal")
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW control_resumen_usuario")
            conn.commit()

        # Refrescar control_resumen_proyecto
        try:
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY control_resumen_proyecto")
            conn.commit()
        except Exception as e2:
            conn.rollback()
            logger.warning(f"CONCURRENT falló para control_resumen_proyecto ({e2}), usando modo normal")
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW control_resumen_proyecto")
            conn.commit()

        log_control(current_user_id, "refresh_stats_control", modulo="control",
                    detalle="Vistas materializadas refrescadas")
        return jsonify({"ok": True, "mensaje": "Estadísticas actualizadas"})
    except Exception as e:
        logger.error(f"Error en refresh_stats: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)


@app.route("/control/export_pdf", methods=["GET"])
@session_required
def control_export_pdf(current_user_id):
    """
    Genera un PDF ejecutivo con los KPIs del módulo de control.
    Usa reportlab si está disponible; si no, genera HTML like fallback.
    """
    import io, json as _json
    from datetime import datetime as dt

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_acciones,
                    COUNT(DISTINCT user_id) AS usuarios_activos,
                    COUNT(DISTINCT entidad_id) FILTER (WHERE entidad_tipo='proyecto') AS proyectos_accedidos,
                    COUNT(*) FILTER (WHERE exitoso = FALSE) AS acciones_fallidas,
                    COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '24 hours') AS acciones_hoy,
                    COUNT(*) FILTER (WHERE fecha >= NOW() - INTERVAL '7 days') AS acciones_semana
                FROM control_actividad
            """)
            totales = dict(cur.fetchone())

            cur.execute("""
                SELECT ca.user_id, u.nombre, COUNT(*) AS total
                FROM control_actividad ca
                LEFT JOIN users u ON u.user_id = ca.user_id
                GROUP BY ca.user_id, u.nombre ORDER BY total DESC LIMIT 10
            """)
            top_usuarios = cur.fetchall()

            cur.execute("""
                SELECT entidad_id, entidad_nombre, COUNT(*) AS total
                FROM control_actividad WHERE entidad_tipo='proyecto' AND entidad_id IS NOT NULL
                GROUP BY entidad_id, entidad_nombre ORDER BY total DESC LIMIT 10
            """)
            top_proyectos = cur.fetchall()

            cur.execute("""
                SELECT accion, COUNT(*) AS total
                FROM control_actividad GROUP BY accion ORDER BY total DESC LIMIT 10
            """)
            top_acciones = cur.fetchall()

            cur.execute("""
                SELECT DATE(fecha AT TIME ZONE 'America/Santiago') AS dia, COUNT(*) AS total
                FROM control_actividad WHERE fecha >= NOW() - INTERVAL '30 days'
                GROUP BY dia ORDER BY dia
            """)
            actividad_diaria = cur.fetchall()

        # ─── Intentar generar PDF con reportlab ───
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                            Table, TableStyle, HRFlowable)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4,
                                    leftMargin=2*cm, rightMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story  = []

            # Estilo personalizado
            title_style = ParagraphStyle('title_ctrl',
                parent=styles['Heading1'],
                fontSize=18, textColor=colors.HexColor('#4f46e5'),
                spaceAfter=6, alignment=TA_CENTER)
            sub_style = ParagraphStyle('sub_ctrl',
                parent=styles['Normal'],
                fontSize=10, textColor=colors.grey,
                spaceAfter=16, alignment=TA_CENTER)
            h2_style = ParagraphStyle('h2_ctrl',
                parent=styles['Heading2'],
                fontSize=13, textColor=colors.HexColor('#1e293b'),
                spaceBefore=16, spaceAfter=8)

            now_str = dt.now().strftime("%d/%m/%Y %H:%M")
            story.append(Paragraph("📊 MÓDULO DE CONTROL – INFORME EJECUTIVO", title_style))
            story.append(Paragraph(f"Generado: {now_str}", sub_style))
            story.append(HRFlowable(width="100%", thickness=2,
                                    color=colors.HexColor('#4f46e5')))
            story.append(Spacer(1, 0.4*cm))

            # ── KPI Globales ──
            story.append(Paragraph("1. KPI Globales del Sistema", h2_style))
            kpi_data = [
                ["Indicador", "Valor"],
                ["Total Acciones Registradas",   str(totales.get("total_acciones", 0))],
                ["Usuarios Únicos Activos",       str(totales.get("usuarios_activos", 0))],
                ["Proyectos Accedidos",           str(totales.get("proyectos_accedidos", 0))],
                ["Acciones Fallidas",             str(totales.get("acciones_fallidas", 0))],
                ["Acciones Hoy (24h)",            str(totales.get("acciones_hoy", 0))],
                ["Acciones Última Semana",        str(totales.get("acciones_semana", 0))],
            ]
            t = Table(kpi_data, colWidths=[10*cm, 5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,0), (-1,-1), 10),
                ('ALIGN',      (1,0), (1,-1), 'CENTER'),
                ('ROWBACKGROUNDS', (0,1), (-1,-1),
                    [colors.HexColor('#f8fafc'), colors.white]),
                ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))

            # ── Top usuarios ──
            story.append(Paragraph("2. Top 10 Usuarios Más Activos", h2_style))
            u_data = [["#", "Usuario", "Total Acciones"]]
            for i, row in enumerate(top_usuarios, 1):
                u_data.append([str(i), row.get("nombre","—"), str(row.get("total",0))])
            t2 = Table(u_data, colWidths=[1*cm, 10*cm, 4*cm])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#10b981')),
                ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,0), (-1,-1), 9),
                ('ROWBACKGROUNDS', (0,1), (-1,-1),
                    [colors.HexColor('#f0fdf4'), colors.white]),
                ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING',    (0,0), (-1,-1), 5),
            ]))
            story.append(t2)
            story.append(Spacer(1, 0.5*cm))

            # ── Top proyectos ──
            story.append(Paragraph("3. Top 10 Proyectos Más Accedidos", h2_style))
            p_data = [["#", "Proyecto", "Total Accesos"]]
            for i, row in enumerate(top_proyectos, 1):
                nombre = (row.get("entidad_nombre") or "—")[:60]
                p_data.append([str(i), nombre, str(row.get("total",0))])
            t3 = Table(p_data, colWidths=[1*cm, 10*cm, 4*cm])
            t3.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f59e0b')),
                ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,0), (-1,-1), 9),
                ('ROWBACKGROUNDS', (0,1), (-1,-1),
                    [colors.HexColor('#fffbeb'), colors.white]),
                ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING',    (0,0), (-1,-1), 5),
            ]))
            story.append(t3)
            story.append(Spacer(1, 0.5*cm))

            # ── Top acciones ──
            story.append(Paragraph("4. Acciones Más Frecuentes", h2_style))
            a_data = [["Acción", "Frecuencia"]]
            for row in top_acciones:
                a_data.append([row.get("accion","—"), str(row.get("total",0))])
            t4 = Table(a_data, colWidths=[10*cm, 5*cm])
            t4.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8b5cf6')),
                ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,0), (-1,-1), 9),
                ('ROWBACKGROUNDS', (0,1), (-1,-1),
                    [colors.HexColor('#f5f3ff'), colors.white]),
                ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING',    (0,0), (-1,-1), 5),
            ]))
            story.append(t4)

            doc.build(story)
            buf.seek(0)
            log_control(current_user_id, "exportar_pdf", modulo="control",
                        detalle="PDF de control exportado")
            return send_file(buf, mimetype="application/pdf",
                             as_attachment=True,
                             download_name=f"informe_control_{dt.now().strftime('%Y%m%d_%H%M')}.pdf")

        except ImportError:
            # Fallback: JSON estructurado si reportlab no está instalado
            log_control(current_user_id, "exportar_pdf_fallback", modulo="control",
                        detalle="reportlab no disponible – retornando JSON")
            return jsonify({
                "advertencia": "reportlab no instalado – datos en JSON",
                "totales": totales,
                "top_usuarios": top_usuarios,
                "top_proyectos": top_proyectos,
                "top_acciones": top_acciones
            })

    except Exception as e:
        logger.error(f"Error en control_export_pdf: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: release_db_connection(conn)


# ── Fin Módulo de Control ──────────────────────────────────────

# -----------------------
# START
# -----------------------
if __name__ == '__main__':
    try:
        cert_path = os.path.abspath("fullchain.pem")
        key_path = os.path.abspath("private.key")
        logger.info("Iniciando servidor en https://0.0.0.0:8000")
        logger.info("Endpoint de health check disponible en: https://0.0.0.0:8000/health")
        logger.info("Sistema optimizado para Railway (PostgreSQL)")
        app.run(host='0.0.0.0', port=8000, ssl_context=(cert_path, key_path))
    finally:
        cleanup()


# app.py - Versión mejorada con manejo robusto de desconexiones de NeonDB
import os
import traceback
import time
import psycopg2
import psycopg2.extras
import psycopg2.pool
import bcrypt
import secrets
import threading
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
import zipfile
import io
import json

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
DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_xHS7sA1FDPqI@ep-hidden-grass-a4sa46kc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
)
APP_HOST = "0.0.0.0"
APP_PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")

app = Flask(__name__)
# CORS(app) - Usaremos manejo manual para garantizar compatibilidad total

@app.after_request
def add_cors_headers(response):
    # Log de tráfico para depuración
    if request.path.startswith('/api'):
        logger.info(f"REQUEST {request.method} {request.path} -> {response.status_code}")
    
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Access-Control-Allow-Credentials'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    # Inyectar headers CORS también en errores
    response = jsonify({"error": str(e)})
    response.status_code = 500
    if hasattr(e, 'code'):
        response.status_code = e.code
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Access-Control-Allow-Credentials'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

logger.info("Backend Municipal (versión mejorada con manejo de desconexiones NeonDB) iniciando...")

# Pool de conexiones global
connection_pool = None
pool_lock = threading.Lock()

# Sesiones simples en memoria { token: user_id }
active_sessions = {}

# Variable para controlar el health check
health_check_thread = None
health_check_running = False

# -----------------------
# UTIL: inicialización y gestión del pool de conexiones
# -----------------------
def init_connection_pool(max_retries=5):
    """
    Inicializa el pool de conexiones a la base de datos con reintentos
    NeonDB puede desconectar conexiones inactivas, por lo que necesitamos
    un pool que se recupere automáticamente
    """
    global connection_pool
    
    for attempt in range(max_retries):
        try:
            with pool_lock:
                # Si ya hay un pool activo, cerrarlo primero
                if connection_pool and not connection_pool.closed:
                    try:
                        connection_pool.closeall()
                        logger.info("Pool anterior cerrado correctamente")
                    except Exception as e:
                        logger.warning(f"Error cerrando pool anterior: {e}")
                
                # Crear nuevo pool con parámetros optimizados para NeonDB
                connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,        # Mínimo de conexiones
                    maxconn=10,       # Máximo de conexiones
                    dsn=DB_CONNECTION_STRING,
                    # Parámetros de keepalive para mantener conexiones activas
                    keepalives=1,
                    keepalives_idle=30,     # Tiempo de inactividad antes de enviar keepalive
                    keepalives_interval=10, # Intervalo entre keepalives
                    keepalives_count=5,     # Número de keepalives antes de desconectar
                    # Timeout de conexión
                    connect_timeout=10,
                    # Otras opciones útiles para NeonDB
                    application_name="municipal_api"
                )
                
                # Verificar que el pool funciona
                test_conn = connection_pool.getconn()
                with test_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                connection_pool.putconn(test_conn)
                
                logger.info("Pool de conexiones inicializado correctamente")
                return True
                
        except Exception as e:
            logger.error(f"Intento {attempt + 1} de inicialización del pool fallido: {e}")
            if attempt < max_retries - 1:
                # Backoff exponencial
                wait_time = (2 ** attempt) + 1
                logger.info(f"Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                logger.error("No se pudo inicializar el pool después de varios intentos")
                connection_pool = None
                return False

def is_connection_error(exception):
    """
    Determina si una excepción está relacionada con problemas de conexión
    """
    error_messages = [
        "connection", "timeout", "closed", "terminated", "reset", 
        "network", "unreachable", "refused", "broken", "idle"
    ]
    error_str = str(exception).lower()
    return any(msg in error_str for msg in error_messages)

def get_db_connection(max_retries=3):
    """
    Obtiene una conexión del pool con reintentos automáticos y manejo robusto de errores
    Específicamente diseñado para manejar las desconexiones periódicas de NeonDB
    """
    global connection_pool
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Si el pool no existe o está cerrado, inicializarlo
            if connection_pool is None or connection_pool.closed:
                logger.info("Pool no disponible, inicializando...")
                if not init_connection_pool():
                    raise Exception("No se pudo inicializar el pool de conexiones")
            
            # Obtener conexión del pool
            conn = connection_pool.getconn()
            
            # Verificar que la conexión funciona (health check rápido)
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    # Si llegamos aquí, la conexión está activa
                    return conn
            except Exception as e:
                # La conexión no es válida, devolverla y marcar para cierre
                logger.warning(f"Conexión no válida detectada: {e}")
                try:
                    connection_pool.putconn(conn, close=True)
                except:
                    pass
                raise e
                
        except Exception as e:
            last_exception = e
            logger.warning(f"Intento {attempt + 1} de conexión fallido: {e}")
            
            # Si es un error de conexión, intentar reinicializar el pool
            if is_connection_error(e):
                logger.info("Detectado error de conexión, reinicializando pool...")
                try:
                    with pool_lock:
                        if connection_pool and not connection_pool.closed:
                            connection_pool.closeall()
                        connection_pool = None
                except Exception as pool_error:
                    logger.error(f"Error cerrando el pool: {pool_error}")
            
            if attempt < max_retries - 1:
                # Backoff exponencial
                wait_time = (2 ** attempt) + 1
                logger.info(f"Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
    
    # Si llegamos aquí, todos los intentos fallaron
    logger.error(f"No se pudo establecer conexión después de {max_retries} intentos")
    raise last_exception or Exception("Error desconocido al obtener conexión")

def release_db_connection(conn):
    """Devuelve la conexión al pool de forma segura"""
    try:
        if connection_pool and conn:
            connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error al devolver la conexión al pool: {e}")
        try:
            conn.close()
        except:
            pass

def health_check_worker():
    """
    Worker que se ejecuta en segundo plano para verificar el estado del pool
    y reinicializarlo si es necesario
    """
    global health_check_running, connection_pool
    
    while health_check_running:
        try:
            if connection_pool and not connection_pool.closed:
                # Intentar obtener una conexión y hacer una consulta simple
                conn = None
                try:
                    conn = connection_pool.getconn()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    logger.debug("Health check del pool: OK")
                except Exception as e:
                    logger.warning(f"Health check del pool falló: {e}")
                    # Si hay un error, reinicializar el pool
                    try:
                        with pool_lock:
                            if connection_pool and not connection_pool.closed:
                                connection_pool.closeall()
                            connection_pool = None
                        init_connection_pool()
                    except Exception as pool_error:
                        logger.error(f"Error reinicializando el pool: {pool_error}")
                finally:
                    if conn:
                        try:
                            connection_pool.putconn(conn)
                        except:
                            pass
            else:
                logger.info("Pool no disponible durante health check, intentando inicializar...")
                init_connection_pool()
            
            # Esperar antes del siguiente health check
            time.sleep(30)  # Health check cada 30 segundos
        except Exception as e:
            logger.error(f"Error en health check worker: {e}")
            time.sleep(180)  # Esperar más tiempo si hay un error

def start_health_check():
    """Inicia el worker de health check en segundo plano"""
    global health_check_thread, health_check_running
    
    if not health_check_running:
        health_check_running = True
        health_check_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_check_thread.start()
        logger.info("Health check worker iniciado")

def stop_health_check():
    """Detiene el worker de health check"""
    global health_check_running
    
    if health_check_running:
        health_check_running = False
        if health_check_thread and health_check_thread.is_alive():
            health_check_thread.join(timeout=5)
        logger.info("Health check worker detenido")

# -----------------------
# UTIL: crear tablas si no existen
# -----------------------
def ensure_tables():
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD para crear tablas.")
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
                activo BOOLEAN DEFAULT TRUE,
                fecha_ultimo_login TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS roles (
                role_id SERIAL PRIMARY KEY,
                nombre TEXT UNIQUE NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                role_id INTEGER REFERENCES roles(role_id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
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

        with conn.cursor() as cur:
            for s in ddl:
                cur.execute(s)
        conn.commit()
        logger.info("Tablas verificadas/creadas correctamente")
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)

# Inicializar pool y crear tablas al inicio
if init_connection_pool():
    ensure_tables()
    start_health_check()
else:
    logger.error("No se pudo inicializar el pool de conexiones al inicio")

# -----------------------
# UTIL: auditoría
# -----------------------
def log_auditoria(user_id, accion, descripcion):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.warning(f"No se pudo registrar auditoría: {accion} - {descripcion}")
            return
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auditoria (user_id, accion, descripcion) VALUES (%s, %s, %s)",
                (user_id, accion, descripcion)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Error en auditoría: {e}")
        traceback.print_exc()
    finally:
        if conn:
            release_db_connection(conn)

# -----------------------
# DECORADOR: session_required
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
    return jsonify({"message": "API Municipal funcionando (con manejo robusto de NeonDB)"})

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
            "neondb_optimized": True
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

        if token in active_sessions:
            del active_sessions[token]

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
                       d.nombre AS division, u.activo
                FROM users u
                LEFT JOIN divisiones d ON u.division_id = d.division_id
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error en get_users: {e}")
        traceback.print_exc()
        return jsonify({"message": "Error interno"}), 500
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

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Error de conexión a BD"}), 500
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (email, password_hash, nombre, nivel_acceso, division_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
            """, (data["email"], hashed, data["nombre"], data["nivel_acceso"], division_id))
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

@app.route("/proyectos", methods=["POST"])
@session_required
def create_proyecto(current_user_id):
    conn = None
    try:
        data = request.get_json()

        forbidden = {"id", "user_id", "actualizado_por", "fecha_actualizacion"}
        data = {k: v for k, v in data.items() if k not in forbidden}

        data["user_id"] = current_user_id
        data["actualizado_por"] = current_user_id

        cols = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))

        sql = f"""
            INSERT INTO proyectos ({cols})
            VALUES ({placeholders})
            RETURNING id
        """

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, tuple(data.values()))
            pid = cur.fetchone()[0]

        conn.commit()

        return jsonify({
            "message": "Proyecto creado",
            "proyecto_id": pid
        }), 201

    finally:
        if conn:
            release_db_connection(conn)

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
    """Cierra el pool de conexiones y detiene el health check al terminar la aplicación"""
    global connection_pool
    
    # Detener el health check worker
    stop_health_check()
    
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

        # Generar token de sesión simple
        import secrets
        token = secrets.token_hex(32)
        active_sessions[token] = u['user_id']
        
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

        # VALIDACIÓN GEOGRÁFICA (Algarrobo, Chile)
        #try:
            #lat, lng = float(d['latitud']), float(d['longitud'])
            # Bounding box estimado: 
            # Norte: -33.20 (Tunquén)
            # Sur: -33.45 (Límite El Quisco/El Tabo margen)
            # Oeste: -71.80 (Mar)
            # Este: -71.50 (Interior)
            #if not (-33.45 <= lat <= -33.20 and -71.80 <= lng <= -71.50):
            #    return jsonify({"msg": "La ubicación no corresponde a la comuna de Algarrobo"}), 400
        #except ValueError:
             #return jsonify({"msg": "Coordenadas inválidas"}), 400
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""INSERT INTO reportes_ciudadanos 
                        (categoria_id, estado_id, latitud, longitud, direccion_referencia, 
                         descripcion, reportado_por, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                        RETURNING id, numero_folio""",
                     (d['categoria_id'], 1, d['latitud'], d['longitud'], 
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
            c.execute("""SELECT r.id, r.numero_folio, c.nombre as categoria, e.nombre as estado,
                        r.direccion_referencia, r.descripcion, r.fecha_reporte, r.latitud, r.longitud,
                        u.nombre as autor
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
                        LEFT JOIN users u ON u.user_id = r.reportado_por
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
    # Endpoint público para el mapa
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("""SELECT r.id, r.latitud, r.longitud, c.nombre as categoria, 
                        e.nombre as estado, r.estado_id, r.direccion_referencia, r.categoria_id,
                        r.fecha_reporte
                        FROM reportes_ciudadanos r
                        LEFT JOIN categorias_reporte c ON c.id = r.categoria_id
                        LEFT JOIN estados_reporte e ON e.id = r.estado_id
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
# MOBILE API: VERIFICACIÓN
# ============================================
@app.route("/api/mobile/reportes/<int:rid>/verificar", methods=["POST"])
@session_required
def verificar_reporte(current_user_id, rid):
    conn = None
    try:
        d = request.get_json()
        estado_id = d.get('estado_id')
        resultado = d.get('resultado') # Compatibilidad
        
        new_status = 1
        if estado_id:
            new_status = int(estado_id)
        elif resultado:
            if resultado == 'CONFIRMADO': new_status = 2
            elif resultado == 'RECHAZADO': new_status = 5
            
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            # 1. Validar que el estado existe en la BD y obtener su nombre
            c.execute("SELECT nombre FROM estados_reporte WHERE id = %s", (new_status,))
            estado_row = c.fetchone()
            
            if not estado_row:
                 return jsonify({"msg":"Estado inválido (no existe en BD)"}), 400
            
            nombre_estado = estado_row['nombre']
            
            # Usamos el nombre del estado (ej: 'Programado') como resultado
            # Nota: Asegurarse que el CHECK constraint en reportes_verificaciones permita estos valores
            # o que la tabla de estados coincida con los valores permitidos.
            
            c.execute("""INSERT INTO reportes_verificaciones (reporte_id, verificado_por, resultado) 
                        VALUES (%s, %s, %s) RETURNING id""", (rid, current_user_id, nombre_estado))
            
            # Actualizar estado reporte
            c.execute("UPDATE reportes_ciudadanos SET estado_id = %s WHERE id = %s", (new_status, rid))
            
        conn.commit()
        return jsonify({"msg":f"Estado actualizado a {nombre_estado}"}), 200
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error verify: {e}")
        return jsonify({"msg":"Error"}), 500
    finally:
        if conn: release_db_connection(conn)

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


# -----------------------
# START
# -----------------------
if __name__ == '__main__':
    try:
        cert_path = os.path.abspath("fullchain.pem")
        key_path = os.path.abspath("private.key")
        logger.info("Iniciando servidor en https://0.0.0.0:8000")
        logger.info("Endpoint de health check disponible en: https://0.0.0.0:8000/health")
        logger.info("Sistema optimizado para manejar desconexiones periódicas de NeonDB")
        app.run(host='0.0.0.0', port=8000, ssl_context=(cert_path, key_path))
    finally:
        cleanup()
import os
import psycopg2
import psycopg2.extras
import bcrypt
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- CONFIGURACIÓN ---
DB_CONNECTION_STRING = "postgresql://neondb_owner:npg_xHS7sA1FDPqI@ep-hidden-grass-a4sa46kc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
SECRET_KEY = "S3cr3tK3yForJWTSigningAndValidation-UseEnvVarsInProd!"

app = Flask(__name__)
CORS(app)

print("Backend de Proyectos Municipales - Version 1.0 - Iniciando...")


# -------------------------------
#  FUNCIONES AUXILIARES
# -------------------------------

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        return conn
    except Exception as e:
        print(f"Error al conectar a la BD: {e}")
        return None


def token_required(f):
    """ Decorador para validar token JWT """
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except:
                return jsonify({"message": "Formato de token inválido"}), 401

        if not token:
            return jsonify({"message": "Token requerido"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, activo FROM users WHERE user_id = %s", (current_user_id,))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if not user or not user[1]:
                return jsonify({"message": "Token inválido o usuario inactivo"}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expirado"}), 401

        except jwt.InvalidTokenError:
            return jsonify({"message": "Token inválido"}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated


# -------------------------------
#  ENDPOINT: HOME
# -------------------------------

@app.route('/')
def home():
    return jsonify({"message": "Bienvenido a la API de Algarrobo"})


# -------------------------------
#  AUTENTICACIÓN
# -------------------------------

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or "email" not in data or "password" not in data:
        return jsonify({"message": "Credenciales incompletas"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, password_hash, nombre, nivel_acceso 
        FROM users 
        WHERE email = %s
    """, (data['email'],))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"message": "Usuario no encontrado"}), 404

    user_id, stored_hash, nombre, nivel_acceso = user

    # --- FIX CRÍTICO AQUÍ ---
    # Convertir a bytes si viene como str (TEXT en la BD)
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode()

    # Validar contraseña
    if not bcrypt.checkpw(data['password'].encode(), stored_hash):
        return jsonify({"message": "Contraseña incorrecta"}), 401

    # Generar tokens
    access_token = jwt.encode({
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }, SECRET_KEY, algorithm="HS256")

    refresh_token = jwt.encode({
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user_id,
            "nombre": nombre,
            "nivel_acceso": nivel_acceso
        }
    })


@app.route('/auth/refresh', methods=['POST'])
def refresh():
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"message": "Token de refresco requerido"}), 400

    try:
        decoded = jwt.decode(refresh_token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded["user_id"]

        new_access = jwt.encode({
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({"access_token": new_access})

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Refresh token expirado"}), 401

    except jwt.InvalidTokenError:
        return jsonify({"message": "Refresh token inválido"}), 401


@app.route('/auth/logout', methods=['POST'])
@token_required
def logout(current_user_id):
    return jsonify({"message": "Sesión cerrada exitosamente"})


# -------------------------------
#  USUARIOS
# -------------------------------

@app.route('/users', methods=['GET'])
@token_required
def get_all_users(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.user_id, u.email, u.nombre, u.nivel_acceso,
               d.nombre AS division, u.activo
        FROM users u
        LEFT JOIN divisiones d ON u.division_id = d.division_id
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    users = []
    for r in rows:
        users.append({
            "id": r[0],
            "email": r[1],
            "nombre": r[2],
            "nivel_acceso": r[3],
            "division": r[4],
            "activo": r[5]
        })
    return jsonify(users)


@app.route('/users', methods=['POST'])
@token_required
def create_user(current_user_id):
    data = request.get_json()

    required = ["email", "password", "nombre", "nivel_acceso", "division_id"]
    if not all(k in data for k in required):
        return jsonify({"message": "Datos incompletos"}), 400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (email, password_hash, nombre, nivel_acceso, division_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
        """, (data["email"], hashed, data["nombre"], data["nivel_acceso"], data["division_id"]))

        new_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"message": "Usuario creado", "user_id": new_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error", "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user_id, user_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "Sin datos"}), 400

    fields = []
    values = []

    for key in ["nombre", "email", "nivel_acceso", "division_id", "activo"]:
        if key in data:
            fields.append(f"{key} = %s")
            values.append(data[key])

    if not fields:
        return jsonify({"message": "No hay campos válidos"}), 400

    values.append(user_id)

    query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, tuple(values))
        conn.commit()
        return jsonify({"message": "Usuario actualizado"})

    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error", "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# -------------------------------
#  PROYECTOS
# -------------------------------

@app.route('/proyectos', methods=['GET'])
@token_required
def get_all_proyectos(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM proyectos ORDER BY nombre")
    proyectos = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(proyectos)


@app.route('/proyectos', methods=['POST'])
@token_required
def create_proyecto(current_user_id):
    data = request.get_json()

    if not data:
        return jsonify({"message": "Datos vacíos"}), 400

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    query = f"INSERT INTO proyectos ({columns}) VALUES ({placeholders}) RETURNING id"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, tuple(data.values()))
        new_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"message": "Proyecto creado", "proyecto_id": new_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error", "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/proyectos/<int:proyecto_id>', methods=['PUT'])
@token_required
def update_proyecto(current_user_id, proyecto_id):
    data = request.get_json()

    if not data:
        return jsonify({"message": "Sin datos"}), 400

    fields = []
    values = []

    for k, v in data.items():
        fields.append(f"{k} = %s")
        values.append(v)

    values.append(proyecto_id)
    query = f"UPDATE proyectos SET {', '.join(fields)} WHERE id = %s"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, tuple(values))
        conn.commit()
        return jsonify({"message": "Proyecto actualizado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/proyectos/<int:proyecto_id>', methods=['DELETE'])
@token_required
def delete_proyecto(current_user_id, proyecto_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM proyectos WHERE id = %s", (proyecto_id,))
        conn.commit()
        return jsonify({"message": "Proyecto eliminado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# -------------------------------
#  DOCUMENTOS
# -------------------------------

@app.route('/proyectos/<int:proyecto_id>/documentos', methods=['POST'])
@token_required
def add_documento(current_user_id, proyecto_id):
    data = request.get_json()

    if not data or "nombre_archivo" not in data or "url_archivo" not in data:
        return jsonify({"message": "Datos incompletos"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM proyectos WHERE id = %s", (proyecto_id,))
    if not cursor.fetchone():
        return jsonify({"message": "Proyecto no existe"}), 404

    try:
        cursor.execute("""
            INSERT INTO documentos (proyecto_id, nombre_archivo, url_archivo)
            VALUES (%s, %s, %s)
            RETURNING doc_id
        """, (proyecto_id, data["nombre_archivo"], data["url_archivo"]))

        doc_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"message": "Documento agregado", "doc_id": doc_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/proyectos/<int:proyecto_id>/documentos', methods=['GET'])
@token_required
def documentos_by_proyecto(current_user_id, proyecto_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM documentos WHERE proyecto_id = %s ORDER BY fecha_subida DESC", (proyecto_id,))
    docs = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(docs)


# -------------------------------
#  AUDITORÍA
# -------------------------------

@app.route('/auditoria', methods=['GET'])
@token_required
def get_auditoria(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT a.audit_id, u.nombre AS usuario, a.accion, a.descripcion, a.fecha
        FROM auditoria a
        JOIN users u ON a.user_id = u.user_id
        ORDER BY a.fecha DESC
    """)

    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(logs)


# -------------------------------
#  EJECUCIÓN DEL SERVIDOR
# -------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

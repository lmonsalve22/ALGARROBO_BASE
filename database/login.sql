CREATE TABLE divisiones (
    division_id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
);
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(150) NOT NULL,

    nivel_acceso SMALLINT NOT NULL CHECK (nivel_acceso BETWEEN 0 AND 5),
    division_id INT,  -- relación simple 1 usuario = 1 división principal

    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_ultimo_login TIMESTAMP,

    FOREIGN KEY (division_id) REFERENCES divisiones(division_id)
);



CREATE TABLE user_roles (
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);



CREATE TABLE auditoria (
    audit_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    accion VARCHAR(200) NOT NULL,
    descripcion TEXT,
    fecha TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO divisiones (division_id, nombre)
VALUES (1, 'SECPLAN');

INSERT INTO roles (role_id, nombre)
VALUES (1, 'trabajador');

INSERT INTO users (
    user_id, email, password_hash, nombre, nivel_acceso, division_id, activo
)
VALUES (
    1,
    'juan.gonzales@municipio.cl',
    '$2b$12$eIXuPJeSasHdsGxfhVnYgONwI0lZbdbYfQx35dDzKvJG2uTKjplfO', -- hash de "123456"
    'Juan Gonzales',
    3,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
);

INSERT INTO user_roles (user_id, role_id)
VALUES (1, 1);

INSERT INTO auditoria (audit_id, user_id, accion, descripcion)
VALUES (
    1,
    1,
    'login',
    'Usuario Juan Gonzales inició sesión en el sistema desde IP 192.168.10.24'
);


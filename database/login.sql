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

INSERT INTO roles (role_id, nombre)
VALUES 
    --Acceso total al sistema: gestión de usuarios, roles, permisos, proyectos, reportes, configuraciones del municipio.
    (10, 'admin_general'),
    --Puede crear, editar y eliminar proyectos; asignar responsables; ver presupuestos; gestionar estados; aprobar hitos.
    (11, 'admin_proyectos'),
    --Supervisa todos los proyectos de obras, revisa avances, aprueba etapas técnicas, revisa informes de terreno.
    (12, 'director_obras'),
    --Ingresa avances, adjunta documentos técnicos, actualiza hitos, carga fotos, reporta problemas en terreno.
    (13, 'profesional_tecnico'),
    --Gestiona y revisa presupuesto, modifica montos, registra gastos, aprueba disponibilidad presupuestaria.
    (14, 'finanzas'),
     --Revisa el estado global, ve dashboards y reportes, aprueba o rechaza proyectos o modificaciones.
    (15, 'supervisor_alcaldia'),
     --Puede ver toda la información autorizada para publicación pública: avances, costos, contratistas, documentos.
    (16, 'transparencia');

INSERT INTO users (
    user_id, email, password_hash, nombre, nivel_acceso, division_id, activo
)
VALUES 
(
    10,
    'admin_general',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'admin_general',
    10,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
),
(
    11,
    'admin_proyectos',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'admin_proyectos',
    11,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
),
(
    12,
    'director_obras',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'director_obras',
    12,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
),
(
    13,
    'profesional_tecnico',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'profesional_tecnico',
    13,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
),
(
    14,
    'finanzas',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'profesional_tecnico',
    14,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
),
(
    15,
    'supervisor_alcaldia',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'supervisor_alcaldia',
    15,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
),
(
    16,
    'transparencia',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'transparencia',
    16,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
)
;

INSERT INTO users (
    user_id, email, password_hash, nombre, nivel_acceso, division_id, activo
)
VALUES (
    1,
    'juan.gonzales@municipio.cl',
    '$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK', -- hash de "123456"
    'Juan Gonzales',
    3,     -- funcionario/trabajador según estructura de niveles
    1,     -- SECPLAN
    TRUE
);


INSERT INTO user_roles (user_id, role_id)
VALUES (1, 1);

INSERT INTO user_roles (user_id, role_id)
VALUES 
(10, 10),
(11, 11),
(12, 12),
(13, 13),
(14, 14),
(15, 15),
(16, 16);

INSERT INTO auditoria (audit_id, user_id, accion, descripcion)
VALUES (
    1,
    1,
    'login',
    'Usuario Juan Gonzales inició sesión en el sistema desde IP 192.168.10.24'
);


CREATE TABLE proyectos (
    id SERIAL PRIMARY KEY,

    user_id INT NOT NULL REFERENCES users(user_id),
    actualizado_por INT NOT NULL REFERENCES users(user_id),

    n_registro INT,

    area_id INT REFERENCES areas(id),
    lineamiento_estrategico_id INT REFERENCES lineamientos_estrategicos(id),

    financiamiento_id INT REFERENCES financiamientos(id),
    financiamiento_municipal VARCHAR(50),

    nombre TEXT,
    monto NUMERIC,

    anno_elaboracion INT,
    anno_ejecucion INT,

    topografia TEXT,
    planimetrias TEXT,
    ingenieria TEXT,
    perfil_tecnico_economico TEXT,
    documentos TEXT,

    avance_total_porcentaje NUMERIC(5,2),
    avance_total_decimal NUMERIC(10,4),

    estado_proyecto_id INT REFERENCES estados_proyecto(id),
    etapa_proyecto_id INT REFERENCES etapas_proyecto(id),
    estado_postulacion_id INT REFERENCES estados_postulacion(id),

    dupla_profesionales TEXT,
    profesional_1 VARCHAR(150),
    profesional_2 VARCHAR(150),
    profesional_3 VARCHAR(150),
    profesional_4 VARCHAR(150),
    profesional_5 VARCHAR(150),

    fecha_postulacion DATE,
    observaciones TEXT,

    unidad_vecinal VARCHAR(150),
    sector_id INT REFERENCES sectores(id),

    aprobacion_dom VARCHAR(100),
    aprobacion_serviu VARCHAR(100),

    fecha_actualizacion TIMESTAMP DEFAULT NOW(),

    latitud NUMERIC(12,6),
    longitud NUMERIC(12,6),
    activo BOOLEAN DEFAULT TRUE
);


CREATE TABLE proyectos_deprecated (
    id SERIAL PRIMARY KEY,

    -- 🔗 Usuario dueño del proyecto
    user_id INT NOT NULL REFERENCES users(user_id),

    actualizado_por INT NOT NULL REFERENCES users(user_id),

    n_registro INT,
    es_prioridad VARCHAR(20),
    area VARCHAR(150),
    lineamiento_estrategico VARCHAR(300),

    financiamiento_municipal VARCHAR(50),
    financiamiento VARCHAR(100),

    nombre TEXT,
    monto NUMERIC,

    anno_elaboracion INT,
    anno_ejecucion INT,

    topografia TEXT,
    planimetrias TEXT,
    ingenieria TEXT,
    perfil_tecnico_economico TEXT,
    documentos TEXT,

    avance_total_porcentaje NUMERIC(5,2),
    avance_total_decimal NUMERIC(10,4),

    estado_proyecto VARCHAR(150),
    codigo VARCHAR(100),

    etapa_proyecto VARCHAR(150),
    estado_postulacion VARCHAR(150),
    fecha_postulacion DATE,

    observaciones TEXT,

    dupla_profesionales TEXT,
    profesional_1 VARCHAR(150),
    profesional_2 VARCHAR(150),
    profesional_3 VARCHAR(150),
    profesional_4 VARCHAR(150),
    profesional_5 VARCHAR(150),

    unidad_vecinal VARCHAR(150),
    sector VARCHAR(200),

    aprobacion_dom VARCHAR(100),
    aprobacion_serviu VARCHAR(100),

    fecha_actualizacion TIMESTAMP DEFAULT NOW(),

    latitud NUMERIC(12,6),
    longitud NUMERIC(12,6)
);


CREATE TABLE mapas (
    mapa_id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT
);

CREATE TABLE mapas_roles (
    mapa_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (mapa_id, role_id),
    CONSTRAINT fk_mapas_roles_mapa
        FOREIGN KEY (mapa_id)
        REFERENCES mapas (mapa_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_mapas_roles_role
        FOREIGN KEY (role_id)
        REFERENCES roles (role_id)
        ON DELETE CASCADE
);

INSERT INTO mapas (nombre, descripcion)
VALUES 
('Varios', '1.html'),
('Proyectos', '2.html');

INSERT INTO mapas (nombre, descripcion)
VALUES 
('Camara', '3.html');

INSERT INTO mapas_roles (mapa_id, role_id)
VALUES 
(1, 10),
(2, 10),
(1, 11);

INSERT INTO mapas_roles (mapa_id, role_id)
VALUES 
(3, 10);



CREATE TABLE proyectos_documentos (
    documento_id SERIAL PRIMARY KEY,

    proyecto_id INT NOT NULL,
    tipo_documento VARCHAR(100),        -- ej: "Planimetría", "Ingeniería", "Contrato"
    nombre VARCHAR(255),                -- nombre visible del documento
    descripcion TEXT,

    url TEXT,                            -- URL en storage (Supabase, S3, etc)
    archivo_nombre VARCHAR(255),
    archivo_extension VARCHAR(20),
    archivo_size BIGINT,                -- bytes

    fecha_subida TIMESTAMP DEFAULT now(),

    CONSTRAINT fk_documentos_proyecto
        FOREIGN KEY (proyecto_id)
        REFERENCES proyectos (id)
        ON DELETE CASCADE
);

CREATE TABLE proyectos_geomapas (
    geomapa_id SERIAL PRIMARY KEY,

    proyecto_id INT NOT NULL,
    nombre VARCHAR(150),
    descripcion TEXT,

    geojson JSONB NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT now(),

    CONSTRAINT fk_geomapas_proyecto
        FOREIGN KEY (proyecto_id)
        REFERENCES proyectos (id)
        ON DELETE CASCADE
);


CREATE TABLE auditoria2 (
    auditoria_id BIGSERIAL PRIMARY KEY,

    fecha TIMESTAMP NOT NULL DEFAULT now(),

    tabla_nombre TEXT NOT NULL,
    operacion TEXT NOT NULL,                 -- INSERT | UPDATE | DELETE

    registro_id TEXT,                        -- id del registro afectado

    usuario_bd TEXT DEFAULT current_user,    -- usuario PostgreSQL

    ip_origen TEXT,
    aplicacion TEXT,

    query TEXT,                              -- query ejecutada
    datos_antes JSONB,
    datos_despues JSONB
);


CREATE TABLE proyectos_hitos (
    id SERIAL PRIMARY KEY,
    proyecto_id INT NOT NULL REFERENCES proyectos(id),

    fecha DATE NOT NULL,
    observacion TEXT,

    categoria_calendario INT REFERENCES hitoscalendario(id),

    categoria_hito INT REFERENCES hitoscalendario(id),

    creado_por INT NOT NULL REFERENCES users(user_id),
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE proyectos_observaciones (
    id SERIAL PRIMARY KEY,
    proyecto_id INT NOT NULL REFERENCES proyectos(id),
    fecha DATE NOT NULL,
    creado_por INT NOT NULL REFERENCES users(user_id),
    observacion TEXT,
    creado_en TIMESTAMP DEFAULT now()
);



CREATE TABLE financiamiento_plazos (
    id SERIAL PRIMARY KEY,

    financiamiento VARCHAR(50) NOT NULL,
    hito_origen VARCHAR(100) NOT NULL,
    hito_destino VARCHAR(100) NOT NULL,

    dias INT NOT NULL,
    tipo_dia VARCHAR(20) NOT NULL
    -- 'HABILES' | 'CORRIDOS'
);

-- FNDR
INSERT INTO financiamiento_plazos
(financiamiento, hito_origen, hito_destino, dias, tipo_dia)
VALUES
('FNDR', 'RECEPCION_OBSERVACIONES', 'RESPUESTA_OBSERVACIONES', 60, 'CORRIDOS'),
('FNDR', 'APROBACION_CONVENIO', 'INICIO_LICITACION', 90, 'CORRIDOS');

-- FRIL
INSERT INTO financiamiento_plazos
(financiamiento, hito_origen, hito_destino, dias, tipo_dia)
VALUES
('FRIL', 'RECEPCION_OBSERVACIONES', 'RESPUESTA_OBSERVACIONES', 20, 'HABILES'),
('FRIL', 'APROBACION_CONVENIO', 'INICIO_LICITACION', 90, 'CORRIDOS');


CREATE TABLE areas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE financiamientos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE etapas_proyecto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    orden SMALLINT,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE estados_proyecto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    color VARCHAR(30),
    activo BOOLEAN DEFAULT TRUE
);


CREATE TABLE estados_postulacion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE sectores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE lineamientos_estrategicos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(300) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);


CREATE TABLE calendario_eventos (
    id SERIAL PRIMARY KEY,
    -- =================================
    -- Datos visibles en el calendario
    -- =================================
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_termino TIMESTAMP,
    todo_el_dia BOOLEAN DEFAULT TRUE,
    categoria_calendario INT REFERENCES hitoscalendario(id),
    -- =================================
    -- Origen del evento (CLAVE)
    -- =================================
    origen_tipo VARCHAR(50),
    origen_id INT,
    -- Ej:
    -- hito        → proyectos_hitos.id
    -- observacion → proyectos_observaciones.id
    -- manual      → NULL
    -- =================================
    -- Metadatos
    -- =================================
    ubicacion VARCHAR(200),
    activo BOOLEAN DEFAULT TRUE,
    categoria_calendario INT REFERENCES hitoscalendario(id),
    -- =================================
    -- Auditoría
    -- =================================
    creado_por INT NOT NULL REFERENCES users(user_id),
    creado_en TIMESTAMP DEFAULT NOW(),
    -- =================================
    -- Integridad
    -- =================================
    UNIQUE (origen_tipo, origen_id)
);


CREATE TABLE hitoscalendario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    is_hito BOOLEAN DEFAULT TRUE
);

INSERT INTO hitoscalendario (nombre, is_hito) VALUES
-- Tipos de Hito (select tipo_hito)
('RECEPCION_OBSERVACIONES', TRUE),
('RESPUESTA_OBSERVACIONES', TRUE),
('APROBACION_CONVENIO', TRUE),
('INICIO_LICITACION', TRUE),
('APROBACION_URS', TRUE),
('APROBACION_NIVEL_CENTRAL', TRUE),
('OTRO', TRUE),

-- Hitos de proyectos
('HITO_INICIO_PROYECTO', TRUE),
('HITO_TERMINO_PROYECTO', TRUE),
('ENTREGA_IMPORTANTE', TRUE),
('INAUGURACION', TRUE),
('POSTULACION_FONDO', TRUE),
('VENCIMIENTO_PERMISO', TRUE),
('PLAZO_RENDICION', TRUE),

-- Calendario / gestión
('FECHA_ADMINISTRATIVA', FALSE),
('REUNION_COORDINACION', FALSE),
('REUNION_EQUIPO', FALSE),
('VISITA_TERRENO', FALSE),
('COORDINACION_CONTRATISTA', FALSE),

-- Eventos
('EVENTO_MUNICIPAL', FALSE),
('CEREMONIA', FALSE),
('EVENTO_COMUNITARIO_PROYECTO', FALSE)
ON CONFLICT (nombre) DO NOTHING;













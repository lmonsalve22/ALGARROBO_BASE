CREATE TABLE proyectos (
    id SERIAL PRIMARY KEY,

    n_registro INT,                             -- Nº
    es_prioridad VARCHAR(20),                   -- ES PRIORIDAD
    area VARCHAR(150),                          -- ÁREA
    lineamiento_estrategico VARCHAR(300),       -- LINEAMIENTO ESTRATÉGICO

    financiamiento_municipal VARCHAR(50),       -- FINANCIAMIENTO MUNICIPAL
    financiamiento VARCHAR(100),                -- FINANCIAMIENTO

    nombre TEXT,                                -- NOMBRE
    monto NUMERIC,                              -- MONTO

    anno_elaboracion INT,                       -- AÑO DE ELABORACIÓN
    anno_ejecucion INT,                         -- AÑO DE EJECUCIÓN

    topografia TEXT,                            -- TOPOGRAFÍA
    planimetrias TEXT,                          -- PLANIMETRÍAS
    ingenieria TEXT,                            -- INGENIERIA
    perfil_tecnico_economico TEXT,              -- PERFIL TÉCNICO - ECONOMICO
    documentos TEXT,                            -- DOCUMENTOS

    avance_total_porcentaje NUMERIC(5,2),       -- AVANCE TOTAL EN PORCENTAJE
    avance_total_decimal NUMERIC(10,4),         -- AVANCE TOTAL DECIMAL

    estado_proyecto VARCHAR(150),               -- ESTADO DEL PROYECTO
    codigo VARCHAR(100),                        -- CÓDIGO

    etapa_proyecto VARCHAR(150),                -- ETAPA DE PROYECTO
    estado_postulacion VARCHAR(150),            -- ESTADO POSTULACIÓN
    fecha_postulacion DATE,                     -- FECHA DE POSTULACIÓN

    observaciones TEXT,                         -- OBSERVACIONES DEL PROYECTO

    dupla_profesionales TEXT,                   -- DUPLA PROFESIONALES
    profesional_1 VARCHAR(150),                 -- PROFESIONAL 1
    profesional_2 VARCHAR(150),                 -- PROFESIONAL 2
    profesional_3 VARCHAR(150),                 -- PROFESIONAL 3
    profesional_4 VARCHAR(150),                 -- PROFESIONAL 4
    profesional_5 VARCHAR(150),                 -- PROFESIONAL 5

    unidad_vecinal VARCHAR(150),                -- UNIDAD VECINAL
    sector VARCHAR(200),                        -- SECTOR

    aprobacion_dom VARCHAR(100),                -- APROBACIÓN DOM
    aprobacion_serviu VARCHAR(100),             -- APROBACIÓN SERVIU

    fecha_actualizacion DATE,                   -- FECHA DE ACTUALIZACIÓN

    latitud NUMERIC(12,6),                      -- LATITUD
    longitud NUMERIC(12,6)                      -- LONGITUD
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

    tipo_hito VARCHAR(100) NOT NULL,

    fecha DATE NOT NULL,
    observacion TEXT,

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






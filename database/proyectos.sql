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


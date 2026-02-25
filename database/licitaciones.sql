-- licitaciones.sql
-- Estructura para el Módulo de Gestión de Licitaciones (Workflow de 32 pasos)

-- 1. Catálogo maestro de pasos de licitación
-- Esta tabla define los 32 pasos estándar que mencionaste.
CREATE TABLE licitacion_pasos_maestro (
    id_paso SERIAL PRIMARY KEY,
    orden INT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    documento_requerido VARCHAR(255),
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE (orden)
);

-- 2. Tabla principal de Licitaciones
-- Una licitación vinculada a un proyecto de la tabla 'proyectos'.
CREATE TABLE licitaciones (
    id SERIAL PRIMARY KEY,
    proyecto_id INT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    nombre_licitacion VARCHAR(255),
    id_mercado_publico VARCHAR(100), -- ID único de Mercado Público (ej: 1234-56-LP24)
    estado_actual_paso INT DEFAULT 1, -- Indica en qué paso va (FK a licitacion_pasos_maestro)
    estado_licitacion VARCHAR(20) DEFAULT 'Abierta', -- Abierta, Cerrada
    monto_estimado NUMERIC,
    
    usuario_creador INT REFERENCES users(user_id),
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP DEFAULT NOW()
);

-- Garantiza que solo exista UNA licitación abierta por proyecto
CREATE UNIQUE INDEX idx_licitacion_abierta_proyecto 
ON licitaciones (proyecto_id) 
WHERE (estado_licitacion = 'Abierta');

-- 3. Seguimiento Detallado (Workflow)
-- Aquí se registra el avance real de cada uno de los 32 pasos para cada licitación.
CREATE TABLE licitacion_workflow (
    id SERIAL PRIMARY KEY,
    licitacion_id INT NOT NULL REFERENCES licitaciones(id) ON DELETE CASCADE,
    paso_id INT NOT NULL REFERENCES licitacion_pasos_maestro(id_paso),
    
    estado VARCHAR(50) DEFAULT 'Pendiente', -- Pendiente, En Proceso, Completado, Atrasado, N/A
    fecha_planificada DATE,
    fecha_real TIMESTAMP,
    
    observaciones TEXT,
    usuario_id INT REFERENCES users(user_id),
    actualizado_en TIMESTAMP DEFAULT NOW(),

    UNIQUE (licitacion_id, paso_id) -- Un registro de seguimiento por paso por licitación
);

-- 4. Documentos por Paso de Licitación
-- Almacena los archivos subidos específicamente durante el flujo de licitación, independientes de los documentos del proyecto.
CREATE TABLE licitaciones_documentos (
    documento_id SERIAL PRIMARY KEY,
    workflow_id INT NOT NULL REFERENCES licitacion_workflow(id) ON DELETE CASCADE,
    
    tipo_documento VARCHAR(100),
    nombre VARCHAR(255),
    descripcion TEXT,
    
    url TEXT,
    archivo_nombre VARCHAR(255),
    archivo_extension VARCHAR(20),
    archivo_size BIGINT,
    
    usuario_subida INT REFERENCES users(user_id),
    fecha_subida TIMESTAMP DEFAULT NOW()
);

-- 5. Biblioteca de Licitaciones (Plantillas, Bases Tipo, Documentos Generales)
CREATE TABLE licitaciones_biblioteca (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(50), -- Bases Administrativas, Bases Técnicas, etc.
    url TEXT NOT NULL,
    archivo_nombre VARCHAR(255),
    archivo_extension VARCHAR(20),
    archivo_size BIGINT,
    usuario_subida INT REFERENCES users(user_id),
    fecha_subida TIMESTAMP DEFAULT NOW()
);

-- 6. Inserción del catálogo de 32 pasos
INSERT INTO licitacion_pasos_maestro (orden, nombre) VALUES
(1, 'Acuerdo de Concejo'),
(2, 'Decreto de Aprobación de convenio'),
(3, 'Elaboración de bases administrativas'),
(4, 'Elaboración de Decretos Alcaldicios'),
(5, '- Aprueba Bases'),
(6, '– Designa comisión de evaluación'),
(7, '- Designa unidad técnica'),
(8, 'Aprobación de Decretos Alcaldicios'),
(9, 'Publicación Licitación Mercado Publico'),
(10, 'Preguntas por Mercado Publico'),
(11, 'Elaborar decreto aprueba respuestas a preguntas de mercado publico'),
(12, 'Publicación de Decreto aprueba respuestas a preguntas de Mercado Publico'),
(13, 'Presentación de ofertas'),
(14, 'Recepción de Garantía Seriedad de la oferta (si procede)'),
(15, 'Apertura de ofertas'),
(16, 'Evaluación de oferta'),
(17, 'Elaboración de informe de evaluación'),
(18, 'Acuerdo de concejo que aprueba adjudicación'),
(19, 'Elaboración de Decreto de Adjudicación'),
(20, 'Publicación de Decreto de Adjudicación'),
(21, 'Adjudicación de Licitación'),
(22, 'Elaboración de Contrato'),
(23, 'Firma de Contrato'),
(24, 'Recepción de Garantía de fiel cumplimiento de contrato'),
(25, 'Acta de entrega de terreno'),
(26, 'Elaboración de decreto uso de bien nacional de uso publico'),
(27, 'Decreto que aprueba anexo de contrato'),
(28, 'Decreto de comisión de recepción provisoria'),
(29, 'Decreto que aprueba el acta de recepción provisoria'),
(30, 'Recepción de Garantía Correcta ejecución de las obras'),
(31, 'Decreto de comisión de recepción definitiva'),
(32, 'Decreto que aprueba el acta de recepción definitiva');

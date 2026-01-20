-- ============================================
-- BASE DE DATOS SIMPLIFICADA
-- Sistema de Reportes Ciudadanos
-- ============================================

-- 1. ROLES (asume que tabla users y roles ya existen)
INSERT INTO roles (nombre) VALUES ('Vecino'), ('Fiscalizador') ON CONFLICT DO NOTHING;

-- 2. CATEGORÍAS (simplificado - solo nombre)
CREATE TABLE IF NOT EXISTS categorias_reporte (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
);

INSERT INTO categorias_reporte (nombre) VALUES
('Bache'), ('Luz'), ('Aceras'), ('Otro')
ON CONFLICT DO NOTHING;

-- 3. ESTADOS (simplificado - solo nombre)
CREATE TABLE IF NOT EXISTS estados_reporte (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
);

INSERT INTO estados_reporte (nombre) VALUES
('Reportado'), ('Verificado'), ('Programado'), ('Reparado'), ('Descartado')
ON CONFLICT DO NOTHING;

-- 4. REPORTES (TABLA PRINCIPAL - simplificada)
CREATE TABLE IF NOT EXISTS reportes_ciudadanos (
    id SERIAL PRIMARY KEY,
    numero_folio VARCHAR(50) UNIQUE,
    
    -- Categorización
    categoria_id INTEGER NOT NULL REFERENCES categorias_reporte(id),
    estado_id INTEGER NOT NULL DEFAULT 1 REFERENCES estados_reporte(id),
    
    -- Ubicación
    latitud NUMERIC(10,7) NOT NULL,
    longitud NUMERIC(10,7) NOT NULL,
    direccion_referencia TEXT NOT NULL,
    
    -- Detalles
    descripcion TEXT,
    
    -- Usuarios
    reportado_por INTEGER NOT NULL REFERENCES users(user_id),
    
    -- Timestamps
    fecha_reporte TIMESTAMP DEFAULT NOW(),
    
    -- Metadata
    activo BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_reportes_cat ON reportes_ciudadanos(categoria_id);
CREATE INDEX idx_reportes_est ON reportes_ciudadanos(estado_id);
CREATE INDEX idx_reportes_fecha ON reportes_ciudadanos(fecha_reporte DESC);

-- 5. FOTOS (simplificado - sin metadata compleja)
CREATE TABLE IF NOT EXISTS reportes_fotos (
    id SERIAL PRIMARY KEY,
    reporte_id INTEGER NOT NULL REFERENCES reportes_ciudadanos(id) ON DELETE CASCADE,
    ruta_archivo TEXT NOT NULL,
    
    subido_por INTEGER REFERENCES users(user_id),
    subido_en TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fotos_reporte ON reportes_fotos(reporte_id);

-- 6. COMENTARIOS (simplificado)
CREATE TABLE IF NOT EXISTS reportes_comentarios (
    id SERIAL PRIMARY KEY,
    reporte_id INTEGER NOT NULL REFERENCES reportes_ciudadanos(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    comentario TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_comentarios_reporte ON reportes_comentarios(reporte_id);

-- 7. VERIFICACIONES (simplificado - sin ubicación ni observaciones)
CREATE TABLE IF NOT EXISTS reportes_verificaciones (
    id SERIAL PRIMARY KEY,
    reporte_id INTEGER NOT NULL REFERENCES reportes_ciudadanos(id) ON DELETE CASCADE,
    verificado_por INTEGER NOT NULL REFERENCES users(user_id),
    verificado_en TIMESTAMP DEFAULT NOW(),
    resultado VARCHAR(50) NOT NULL CHECK (resultado IN ('CONFIRMADO','RECHAZADO','REQUIERE_TRABAJO','YA_RESUELTO'))
);

-- ============================================
-- TRIGGERS Y FUNCIONES
-- ============================================

-- Auto-generar folio
CREATE OR REPLACE FUNCTION generar_folio() RETURNS TRIGGER AS $$
BEGIN
    NEW.numero_folio := 'REP-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || LPAD(NEW.id::TEXT, 4, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_folio 
AFTER INSERT ON reportes_ciudadanos
FOR EACH ROW 
EXECUTE FUNCTION generar_folio();

-- FIN

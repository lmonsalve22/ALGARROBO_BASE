-- ============================================================
-- MÓDULO DE CONTROL - Auditoría de actividad de usuarios
-- Compatibilidad: PostgreSQL (Railway)
-- Cubre: login/logout, vistas de proyectos, ediciones,
--        creación, eliminación, descarga de documentos,
--        acceso a hitos, observaciones, geomapas, etc.
-- ============================================================

-- ───────────────────────────────────────────────────────────
-- 1. TABLA PRINCIPAL: control_actividad
--    Registra CADA acción del usuario con granularidad alta
-- ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS control_actividad (
    id              BIGSERIAL PRIMARY KEY,

    -- Actor
    user_id         INT REFERENCES users(user_id) ON DELETE SET NULL,

    -- Tipo de acción
    -- login | logout | ver_proyecto | editar_proyecto | crear_proyecto
    -- eliminar_proyecto | ver_lista_proyectos | descargar_documento
    -- subir_documento | ver_hito | crear_hito | editar_hito
    -- ver_observacion | crear_observacion | ver_geomapa | ver_reporte
    -- ver_dashboard | ver_calendario | exportar_pdf | cambio_estado
    -- cambio_etapa | reset_password | crear_usuario | editar_usuario
    -- eliminar_usuario | asignar_roles | ver_control | etc.
    accion          VARCHAR(80) NOT NULL,

    -- Módulo funcional para agrupación analítica
    -- proyectos | auth | usuarios | documentos | reportes | control
    modulo          VARCHAR(40) DEFAULT 'proyectos',

    -- Entidad objetivo (opcional)
    entidad_tipo    VARCHAR(40),   -- 'proyecto' | 'usuario' | 'documento' | 'hito'
    entidad_id      INT,           -- id del proyecto, usuario, documento, etc.
    entidad_nombre  TEXT,          -- nombre descriptivo para trazabilidad

    -- Resultado de la acción
    exitoso         BOOLEAN DEFAULT TRUE,
    detalle         TEXT,          -- detalles adicionales o mensaje de error

    -- Contexto técnico
    ip_origen       INET,
    user_agent      TEXT,
    endpoint        VARCHAR(200),  -- ruta de API llamada

    -- Datos de cambio (antes/después para ediciones)
    datos_antes     JSONB,
    datos_despues   JSONB,

    -- Timestamp
    fecha           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índices para consultas frecuentes en el panel de control
CREATE INDEX IF NOT EXISTS idx_ctrl_user_id   ON control_actividad (user_id);
CREATE INDEX IF NOT EXISTS idx_ctrl_accion    ON control_actividad (accion);
CREATE INDEX IF NOT EXISTS idx_ctrl_fecha     ON control_actividad (fecha DESC);
CREATE INDEX IF NOT EXISTS idx_ctrl_modulo    ON control_actividad (modulo);
CREATE INDEX IF NOT EXISTS idx_ctrl_entidad   ON control_actividad (entidad_tipo, entidad_id);

-- ───────────────────────────────────────────────────────────
-- 2. TABLA: control_sesiones
--    Ciclo de vida completo de cada sesión de usuario
-- ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS control_sesiones (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INT REFERENCES users(user_id) ON DELETE SET NULL,
    token_hash      VARCHAR(64),          -- SHA-256 del token (no almacenar token crudo)
    ip_origen       INET,
    user_agent      TEXT,
    fecha_inicio    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_fin       TIMESTAMP WITH TIME ZONE,
    duracion_seg    INT GENERATED ALWAYS AS (
                        EXTRACT(EPOCH FROM (fecha_fin - fecha_inicio))::INT
                    ) STORED,
    cerrada_por     VARCHAR(20) DEFAULT 'activa',
    -- 'activa' | 'logout' | 'expiracion' | 'admin'
    total_acciones  INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sesion_user     ON control_sesiones (user_id);
CREATE INDEX IF NOT EXISTS idx_sesion_inicio   ON control_sesiones (fecha_inicio DESC);

-- ───────────────────────────────────────────────────────────
-- 3. VISTA MATERIALIZADA: control_resumen_usuario
--    KPI agregados por usuario para el panel de control
--    Se refresca vía endpoint /control/refresh_stats
-- ───────────────────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS control_resumen_usuario AS
SELECT
    u.user_id,
    u.nombre                                        AS nombre_usuario,
    u.email,
    u.nivel_acceso,
    COUNT(ca.id)                                    AS total_acciones,
    COUNT(ca.id) FILTER (WHERE ca.modulo = 'proyectos')  AS acciones_proyectos,
    COUNT(ca.id) FILTER (WHERE ca.accion = 'ver_proyecto')      AS vistas_proyecto,
    COUNT(ca.id) FILTER (WHERE ca.accion = 'editar_proyecto')   AS ediciones_proyecto,
    COUNT(ca.id) FILTER (WHERE ca.accion = 'crear_proyecto')    AS creaciones_proyecto,
    COUNT(ca.id) FILTER (WHERE ca.accion LIKE 'ver_%')          AS total_lecturas,
    COUNT(ca.id) FILTER (WHERE ca.accion LIKE '%editar%' OR ca.accion LIKE '%crear%' OR ca.accion LIKE '%eliminar%') AS total_escrituras,
    COUNT(ca.id) FILTER (WHERE ca.exitoso = FALSE)      AS acciones_fallidas,
    COUNT(DISTINCT ca.entidad_id) FILTER (WHERE ca.entidad_tipo = 'proyecto') AS proyectos_distintos_accedidos,
    MIN(ca.fecha)                                   AS primera_actividad,
    MAX(ca.fecha)                                   AS ultima_actividad,
    COUNT(DISTINCT DATE(ca.fecha AT TIME ZONE 'America/Santiago'))  AS dias_activo
FROM users u
LEFT JOIN control_actividad ca ON ca.user_id = u.user_id
GROUP BY u.user_id, u.nombre, u.email, u.nivel_acceso;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_ctrl_resumen ON control_resumen_usuario (user_id);

-- ───────────────────────────────────────────────────────────
-- 4. VISTA MATERIALIZADA: control_resumen_proyecto
--    KPI de actividad por proyecto para el panel de control
-- ───────────────────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS control_resumen_proyecto AS
SELECT
    p.id                                            AS proyecto_id,
    p.nombre                                        AS nombre_proyecto,
    COUNT(ca.id)                                    AS total_acciones,
    COUNT(ca.id) FILTER (WHERE ca.accion = 'ver_proyecto')      AS total_vistas,
    COUNT(ca.id) FILTER (WHERE ca.accion = 'editar_proyecto')   AS total_ediciones,
    COUNT(DISTINCT ca.user_id)                      AS usuarios_distintos,
    MAX(ca.fecha)                                   AS ultima_actividad,
    MIN(ca.fecha)                                   AS primera_actividad
FROM proyectos p
LEFT JOIN control_actividad ca ON ca.entidad_tipo = 'proyecto' AND ca.entidad_id = p.id
GROUP BY p.id, p.nombre;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_ctrl_resumen_proy ON control_resumen_proyecto (proyecto_id);

-- ───────────────────────────────────────────────────────────
-- 5. FUNCIÓN: registrar_actividad()
--    Permite insertar actividad desde triggers PostgreSQL
--    (usado por triggers en INSERT/UPDATE/DELETE de proyectos)
-- ───────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION registrar_actividad_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_accion TEXT;
    v_datos_antes JSONB;
    v_datos_despues JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_accion := 'crear_proyecto';
        v_datos_antes := NULL;
        v_datos_despues := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_accion := 'editar_proyecto';
        v_datos_antes := to_jsonb(OLD);
        v_datos_despues := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        v_accion := 'eliminar_proyecto';
        v_datos_antes := to_jsonb(OLD);
        v_datos_despues := NULL;
    END IF;

    INSERT INTO control_actividad (
        user_id, accion, modulo,
        entidad_tipo, entidad_id, entidad_nombre,
        datos_antes, datos_despues,
        detalle
    ) VALUES (
        -- En DELETE solo existe OLD; en INSERT solo NEW; en UPDATE ambos
        CASE TG_OP
            WHEN 'DELETE' THEN COALESCE(OLD.actualizado_por, OLD.user_id)
            ELSE              COALESCE(NEW.actualizado_por, NEW.user_id)
        END,
        v_accion, 'proyectos',
        'proyecto',
        CASE TG_OP WHEN 'DELETE' THEN OLD.id   ELSE NEW.id   END,
        CASE TG_OP WHEN 'DELETE' THEN OLD.nombre ELSE NEW.nombre END,
        v_datos_antes,
        v_datos_despues,
        'Registrado automáticamente por trigger'
    );

    -- AFTER trigger: retornar NEW en INSERT/UPDATE, OLD en DELETE
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger de auditoría automática sobre la tabla proyectos
DROP TRIGGER IF EXISTS trg_control_proyectos ON proyectos;
CREATE TRIGGER trg_control_proyectos
AFTER INSERT OR UPDATE OR DELETE ON proyectos
FOR EACH ROW EXECUTE FUNCTION registrar_actividad_trigger();

-- ───────────────────────────────────────────────────────────
-- 6. REGISTRO INICIAL (seed de ejemplo)
--    Usa WHERE NOT EXISTS para evitar duplicados sin necesitar
--    constraint UNIQUE (control_actividad es una tabla de log)
-- ───────────────────────────────────────────────────────────
INSERT INTO control_actividad (user_id, accion, modulo, detalle, ip_origen)
SELECT 10, 'sistema_iniciado', 'sistema', 'Módulo de control activado', '127.0.0.1'
WHERE NOT EXISTS (
    SELECT 1 FROM control_actividad
    WHERE accion = 'sistema_iniciado' AND modulo = 'sistema'
);

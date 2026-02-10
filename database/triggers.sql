CREATE OR REPLACE FUNCTION set_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_DATE;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;



CREATE OR REPLACE FUNCTION auditoria2_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO auditoria2 (
        tabla_nombre,
        operacion,
        registro_id,
        query,
        datos_antes,
        datos_despues
    )
    VALUES (
        TG_TABLE_NAME,
        TG_OP,
        COALESCE(NEW.id::TEXT, OLD.id::TEXT),
        current_query(),
        CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN to_jsonb(NEW) END
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trg_proyectos_fecha_actualizacion
BEFORE UPDATE ON proyectos
FOR EACH ROW
EXECUTE FUNCTION set_fecha_actualizacion();


CREATE OR REPLACE FUNCTION trg_proyectos_insert_hito_postulacion()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO proyectos_hitos (
        proyecto_id,
        categoria_hito,
        fecha,
        observacion,
        creado_por
    )
    VALUES (
        NEW.id,
        (SELECT id FROM hitoscalendario WHERE nombre = 'POSTULACION_FONDO' LIMIT 1),
        COALESCE(NEW.fecha_postulacion, CURRENT_DATE),
        NEW.observaciones,
        NEW.user_id
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_insert_proyectos_hito_postulacion
AFTER INSERT ON proyectos
FOR EACH ROW
EXECUTE FUNCTION trg_proyectos_insert_hito_postulacion();


CREATE OR REPLACE FUNCTION trg_actualizar_proyecto_desde_evento()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE proyectos
    SET
        actualizado_por     = NEW.creado_por,
        observaciones       = NEW.observacion,
        fecha_actualizacion = NOW()
    WHERE id = NEW.proyecto_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER after_insert_proyectos_hitos_actualiza_proyecto
AFTER INSERT ON proyectos_hitos
FOR EACH ROW
EXECUTE FUNCTION trg_actualizar_proyecto_desde_evento();

CREATE TRIGGER after_insert_proyectos_observaciones_actualiza_proyecto
AFTER INSERT ON proyectos_observaciones
FOR EACH ROW
EXECUTE FUNCTION trg_actualizar_proyecto_desde_evento();


CREATE OR REPLACE FUNCTION trg_sync_hito_to_calendario()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO calendario_eventos (
        titulo,
        descripcion,
        fecha_inicio,
        fecha_termino,
        todo_el_dia,
        origen_tipo,
        origen_id,
        creado_por
    )
    VALUES (
        'Hito: ',
        NEW.observacion,
        NEW.fecha::timestamp,
        NULL,
        TRUE,
        'proyectos_hitos',
        NEW.id,
        NEW.creado_por
    )
    ON CONFLICT (origen_tipo, origen_id)
    DO UPDATE SET
        titulo = EXCLUDED.titulo,
        descripcion = EXCLUDED.descripcion,
        fecha_inicio = EXCLUDED.fecha_inicio,
        activo = TRUE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_hito_calendario
AFTER INSERT ON proyectos_hitos
FOR EACH ROW
EXECUTE FUNCTION trg_sync_hito_to_calendario();

CREATE OR REPLACE FUNCTION trg_sync_observacion_to_calendario()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO calendario_eventos (
        titulo,
        descripcion,
        fecha_inicio,
        fecha_termino,
        todo_el_dia,
        origen_tipo,
        origen_id,
        creado_por
    )
    VALUES (
        'Observación de proyecto',
        NEW.observacion,
        NEW.fecha::timestamp,
        NULL,
        TRUE,
        'proyectos_observaciones',
        NEW.id,
        NEW.creado_por
    )
    ON CONFLICT (origen_tipo, origen_id)
    DO UPDATE SET
        descripcion = EXCLUDED.descripcion,
        fecha_inicio = EXCLUDED.fecha_inicio,
        activo = TRUE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_observacion_calendario
AFTER INSERT ON proyectos_observaciones
FOR EACH ROW
EXECUTE FUNCTION trg_sync_observacion_to_calendario();



CREATE OR REPLACE VIEW vw_calendario_eventos_full AS
SELECT
    ce.id AS calendario_id,
    ce.titulo,
    ce.descripcion,
    ce.fecha_inicio,
    ce.fecha_termino,
    ce.todo_el_dia,
    ce.origen_tipo,
    ce.activo,

    -- ======================
    -- Proyecto
    -- ======================
    p.id AS proyecto_id,
    p.nombre AS proyecto_nombre,
    p.monto,
    p.anno_ejecucion,
    p.fecha_postulacion,

    -- ======================
    -- Normalizados (nombres)
    -- ======================
    a.nombre  AS area_nombre,
    f.nombre  AS financiamiento_nombre,
    ep.nombre AS estado_proyecto,
    et.nombre AS etapa_proyecto,
    es.nombre AS estado_postulacion,
    s.nombre  AS sector_nombre,

    -- ======================
    -- Metadata del origen
    -- ======================
    ph.fecha        AS hito_fecha,
    ph.observacion  AS hito_observacion,

    po.observacion  AS observacion_texto,

    ce.creado_por,
    ce.creado_en

FROM calendario_eventos ce

-- ======================
-- Resolver ORIGEN
-- ======================
LEFT JOIN proyectos_hitos ph
    ON ce.origen_tipo = 'proyectos_hitos'
   AND ce.origen_id = ph.id

LEFT JOIN proyectos_observaciones po
    ON ce.origen_tipo = 'proyectos_observaciones'
   AND ce.origen_id = po.id

-- ======================
-- Resolver PROYECTO
-- ======================
LEFT JOIN proyectos p
    ON p.id = COALESCE(ph.proyecto_id, po.proyecto_id)

-- ======================
-- Catálogos
-- ======================
LEFT JOIN areas a ON a.id = p.area_id
LEFT JOIN financiamientos f ON f.id = p.financiamiento_id
LEFT JOIN estados_proyecto ep ON ep.id = p.estado_proyecto_id
LEFT JOIN etapas_proyecto et ON et.id = p.etapa_proyecto_id
LEFT JOIN estados_postulacion es ON es.id = p.estado_postulacion_id
LEFT JOIN sectores s ON s.id = p.sector_id

WHERE ce.activo = TRUE;






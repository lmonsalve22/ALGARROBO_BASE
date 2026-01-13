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
        tipo_hito,
        fecha,
        observacion,
        creado_por
    )
    VALUES (
        NEW.id,
        'Postulación',
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
        'Hito: ' || NEW.tipo_hito,
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





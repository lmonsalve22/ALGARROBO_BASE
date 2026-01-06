CREATE OR REPLACE FUNCTION set_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_DATE;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_proyectos_fecha_actualizacion
BEFORE UPDATE ON proyectos
FOR EACH ROW
EXECUTE FUNCTION set_fecha_actualizacion();

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


ALTER TABLE proyectos
ADD COLUMN user_id INT;

ALTER TABLE proyectos
ALTER COLUMN user_id SET DEFAULT 10;

UPDATE proyectos
SET user_id = 10
WHERE user_id IS NULL;


ALTER TABLE proyectos
ADD COLUMN actualizado_por  INT;

ALTER TABLE proyectos
ALTER COLUMN actualizado_por SET DEFAULT 10;

UPDATE proyectos
SET actualizado_por = 10
WHERE actualizado_por IS NULL;

-- Migration script to convert Actor.id_number from string to JSONB array
-- This script converts existing string values into single-element JSON arrays with default type (1)

-- First, ensure there is an IDNumberType entity with id 1 in the database
INSERT INTO id_number_types (id, title, title_tr, created_at, updated_at, deleted) 
VALUES (1, 'National ID', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE) 
ON CONFLICT (id) DO NOTHING;

-- Create a backup of the current data
CREATE TABLE IF NOT EXISTS actor_id_number_backup AS 
SELECT id, id_number 
FROM actor 
WHERE id_number IS NOT NULL AND id_number != '';

-- Create temporary column to store the new JSONB data
ALTER TABLE actor ADD COLUMN id_number_temp JSONB;

-- Migrate existing string data to JSONB array format
UPDATE actor 
SET id_number_temp = CASE 
    WHEN id_number IS NOT NULL AND id_number != '' 
    THEN jsonb_build_array(jsonb_build_object('type', '1', 'number', id_number))
    ELSE '[]'::jsonb
END;

-- Drop the old column
ALTER TABLE actor DROP COLUMN id_number;

-- Rename the temporary column
ALTER TABLE actor RENAME COLUMN id_number_temp TO id_number;

-- Set default value and not null constraint
ALTER TABLE actor ALTER COLUMN id_number SET DEFAULT '[]'::jsonb;
ALTER TABLE actor ALTER COLUMN id_number SET NOT NULL;

-- Add check constraint to ensure id_number is an array
ALTER TABLE actor ADD CONSTRAINT check_actor_id_number_is_array 
CHECK (jsonb_typeof(id_number) = 'array');

-- Add check constraint to ensure each element has string type and number keys
ALTER TABLE actor ADD CONSTRAINT check_actor_id_number_element_structure 
CHECK (
    id_number = '[]'::jsonb OR 
    (
        SELECT bool_and(
            jsonb_typeof(elem->'type') = 'string' AND 
            jsonb_typeof(elem->'number') = 'string' AND
            (elem->'type') IS NOT NULL AND 
            (elem->'number') IS NOT NULL
        ) 
        FROM jsonb_array_elements(id_number) AS elem
    )
);

-- Add check constraint to ensure valid IDNumberType references
ALTER TABLE actor ADD CONSTRAINT check_actor_id_number_valid_type_references 
CHECK (
    id_number = '[]'::jsonb OR 
    (
        SELECT bool_and(
            EXISTS (
                SELECT 1 FROM id_number_types 
                WHERE id = (elem->>'type')::int AND deleted = FALSE
            )
        ) 
        FROM jsonb_array_elements(id_number) AS elem
    )
);

-- Create an index for better performance on JSONB queries
CREATE INDEX IF NOT EXISTS ix_actor_id_number_gin ON actor USING GIN (id_number);

-- Rollback script (commented out):
/*
-- To rollback this migration:
-- 1. Remove constraints
ALTER TABLE actor DROP CONSTRAINT IF EXISTS check_actor_id_number_is_array;
ALTER TABLE actor DROP CONSTRAINT IF EXISTS check_actor_id_number_element_structure;
ALTER TABLE actor DROP CONSTRAINT IF EXISTS check_actor_id_number_valid_type_references;

-- 2. Drop index
DROP INDEX IF EXISTS ix_actor_id_number_gin;

-- 3. Add temporary string column
ALTER TABLE actor ADD COLUMN id_number_temp VARCHAR(255);

-- 4. Convert JSONB back to string (taking first element's number)
UPDATE actor 
SET id_number_temp = CASE 
    WHEN jsonb_array_length(id_number) > 0 
    THEN id_number->0->>'number'
    ELSE NULL
END;

-- 5. Drop JSONB column and rename temp column
ALTER TABLE actor DROP COLUMN id_number;
ALTER TABLE actor RENAME COLUMN id_number_temp TO id_number;

-- 6. Restore data from backup if needed
-- UPDATE actor SET id_number = backup.id_number 
-- FROM actor_id_number_backup backup 
-- WHERE actor.id = backup.id;

-- 7. Drop backup table
DROP TABLE IF EXISTS actor_id_number_backup;
*/ 
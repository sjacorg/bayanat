-- Rename ref column to tags
ALTER TABLE export RENAME COLUMN ref TO tags;

-- Update any null values to empty array
UPDATE export SET tags = '{}' WHERE tags IS NULL;

-- Set tags column to be non-nullable with default empty array
ALTER TABLE export 
    ALTER COLUMN tags SET NOT NULL,
    ALTER COLUMN tags SET DEFAULT '{}';


-- Rollback script:
/*
-- Remove NOT NULL constraint and default value
ALTER TABLE export 
    ALTER COLUMN tags DROP NOT NULL,
    ALTER COLUMN tags DROP DEFAULT;

-- Rename tags back to ref
ALTER TABLE export RENAME COLUMN tags TO ref;
*/


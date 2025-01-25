
-- 1. Add the tags_search column
ALTER TABLE bulletin 
ADD COLUMN tags_search TEXT NOT NULL DEFAULT '';

-- 2. Populate existing records
UPDATE bulletin 
SET tags_search = array_to_string(tags, ' ', '');

-- 3. Create the trigram index
CREATE INDEX ix_bulletin_tags_search ON bulletin USING gin (tags_search gin_trgm_ops);
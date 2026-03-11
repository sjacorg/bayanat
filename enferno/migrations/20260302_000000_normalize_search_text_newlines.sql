-- Collapse newlines in extraction.search_text for cross-line search matching.
-- The normalize_arabic_text() function now replaces newlines with spaces.
-- Recreate the generated column to recompute all stored values.

ALTER TABLE extraction DROP COLUMN IF EXISTS search_text;
ALTER TABLE extraction ADD COLUMN search_text text GENERATED ALWAYS AS (normalize_arabic_text(text)) STORED;
CREATE INDEX IF NOT EXISTS ix_extraction_search_text_trgm ON extraction USING GIN(search_text gin_trgm_ops);

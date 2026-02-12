-- Migration: Create extraction table for OCR text extraction results

CREATE TABLE IF NOT EXISTS extraction (
    id SERIAL PRIMARY KEY,
    media_id INTEGER NOT NULL UNIQUE,

    -- Extracted content
    text TEXT,
    original_text TEXT,
    raw JSONB,
    confidence FLOAT,
    orientation INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    manual BOOLEAN NOT NULL DEFAULT FALSE,
    word_count INTEGER DEFAULT 0,
    language VARCHAR(10),

    -- Review tracking
    reviewed_by INTEGER,
    reviewed_at TIMESTAMP,

    -- Timestamps (BaseMixin fields)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS ix_extraction_media_id ON extraction (media_id);
CREATE INDEX IF NOT EXISTS ix_extraction_status ON extraction (status);
CREATE INDEX IF NOT EXISTS ix_extraction_confidence ON extraction (confidence);

-- Text normalization function for search indexing.
-- Currently handles Arabic (alef variants, taa marbuta, diacritics, eastern numerals).
-- Non-Arabic text passes through unchanged, so this is safe for all deployments.
CREATE OR REPLACE FUNCTION normalize_arabic_text(input text) RETURNS text AS $$
BEGIN
    IF input IS NULL THEN RETURN NULL; END IF;
    RETURN translate(
        input,
        -- Replacements first (positional mapping to "to" string):
        --   أ إ آ ٱ ى ة ٠ ١ ٢ ٣ ٤ ٥ ٦ ٧ ٨ ٩
        -- Then deletions (no corresponding "to" char):
        --   fathatan dammatan kasratan fatha damma kasra shadda sukun tatweel
        E'\u0623\u0625\u0622\u0671\u0649\u0629\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0640',
        E'\u0627\u0627\u0627\u0627\u064A\u06470123456789'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

-- Generated column for normalized search text
ALTER TABLE extraction ADD COLUMN IF NOT EXISTS search_text TEXT
    GENERATED ALWAYS AS (normalize_arabic_text(text)) STORED;

-- Trigram index for fuzzy/ILIKE search on normalized text.
-- Prerequisite: pg_trgm extension must be installed by a superuser:
--   CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- The database locale must be UTF-8 for proper Arabic trigram support.
CREATE INDEX IF NOT EXISTS ix_extraction_search_text_trgm
    ON extraction USING GIN(search_text gin_trgm_ops);

-- Foreign key constraints
ALTER TABLE extraction
ADD CONSTRAINT fk_extraction_media_id
FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE;

ALTER TABLE extraction
ADD CONSTRAINT fk_extraction_reviewed_by
FOREIGN KEY (reviewed_by) REFERENCES "user"(id);

-- Rollback script:
/*
DROP TABLE IF EXISTS extraction;
*/

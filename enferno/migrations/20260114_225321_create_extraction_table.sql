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

-- Trigram index for fuzzy/ILIKE search on extracted text.
-- Prerequisite: pg_trgm extension must be installed by a superuser:
--   CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- The database locale must be UTF-8 for proper Arabic trigram support.
CREATE INDEX IF NOT EXISTS ix_extraction_text_trgm
    ON extraction USING GIN(text gin_trgm_ops);

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

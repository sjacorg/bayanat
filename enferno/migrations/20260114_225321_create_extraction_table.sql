-- Migration: Create extraction table for OCR text extraction results

CREATE TABLE IF NOT EXISTS extraction (
    id SERIAL PRIMARY KEY,
    media_id INTEGER NOT NULL UNIQUE,

    -- Extracted content
    text TEXT,
    raw JSONB,
    confidence FLOAT,
    orientation INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    manual BOOLEAN NOT NULL DEFAULT FALSE,

    -- Review tracking
    reviewed_by INTEGER,
    reviewed_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS ix_extraction_media_id ON extraction (media_id);
CREATE INDEX IF NOT EXISTS ix_extraction_status ON extraction (status);
CREATE INDEX IF NOT EXISTS ix_extraction_confidence ON extraction (confidence);

-- Full-text search index
CREATE INDEX IF NOT EXISTS ix_extraction_text_fts
    ON extraction USING GIN(to_tsvector('simple', text));

-- Trigram index for fuzzy search (requires pg_trgm extension)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS ix_extraction_text_trgm
    ON extraction USING GIN(text gin_trgm_ops);

-- Foreign key constraints
ALTER TABLE extraction
ADD CONSTRAINT fk_extraction_media_id
FOREIGN KEY (media_id) REFERENCES media(id);

ALTER TABLE extraction
ADD CONSTRAINT fk_extraction_reviewed_by
FOREIGN KEY (reviewed_by) REFERENCES "user"(id);

-- Rollback script:
/*
DROP TABLE IF EXISTS extraction;
*/

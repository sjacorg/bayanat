-- OCR Simplification Migration
-- Adds edit history to extraction, moves orientation to media

-- 1. Add history column to extraction (append-only edit log)
ALTER TABLE extraction ADD COLUMN IF NOT EXISTS history JSONB DEFAULT '[]'::jsonb NOT NULL;

-- 2. Add orientation column to media (independent of OCR)
ALTER TABLE media ADD COLUMN IF NOT EXISTS orientation INTEGER DEFAULT 0;

-- 3. Migrate existing orientation data from extraction to media
UPDATE media SET orientation = e.orientation
FROM extraction e
WHERE e.media_id = media.id AND e.orientation != 0;

-- 4. Auto-process all existing review/transcription items
UPDATE extraction SET status = 'processed'
WHERE status IN ('needs_review', 'needs_transcription');

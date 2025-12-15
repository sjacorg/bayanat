-- Migration: Fix label flag inheritance
-- Description: Cascade parent flags down to all descendants to ensure exact match validation
-- Date: 2025-12-15

BEGIN;

-- Recursive update: children inherit parent's flags
WITH RECURSIVE label_tree AS (
    -- Start with root labels (no parent)
    SELECT id, parent_label_id, for_bulletin, for_actor, for_incident, for_offline, verified
    FROM label
    WHERE parent_label_id IS NULL

    UNION ALL

    -- Children inherit from parent
    SELECT c.id, c.parent_label_id,
           p.for_bulletin, p.for_actor, p.for_incident, p.for_offline, p.verified
    FROM label c
    JOIN label_tree p ON c.parent_label_id = p.id
)
UPDATE label
SET
    for_bulletin = lt.for_bulletin,
    for_actor = lt.for_actor,
    for_incident = lt.for_incident,
    for_offline = lt.for_offline,
    verified = lt.verified
FROM label_tree lt
WHERE label.id = lt.id
  AND label.parent_label_id IS NOT NULL;

COMMIT;

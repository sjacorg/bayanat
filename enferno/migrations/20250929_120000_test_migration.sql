-- Test migration to verify automatic update system
-- This is a no-op migration that can be safely applied and removed

-- Add a comment to a table (safe operation)
COMMENT ON TABLE actor IS 'Individuals or entities involved in incidents';
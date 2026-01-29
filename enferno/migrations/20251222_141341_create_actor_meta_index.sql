CREATE INDEX IF NOT EXISTS ix_actor_meta_gin
ON actor
USING gin (meta);

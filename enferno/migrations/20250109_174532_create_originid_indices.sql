DROP INDEX ix_actor_profile_originid;
DROP INDEX ix_bulletin_originid;

CREATE INDEX IF NOT EXISTS ix_bulletin_originid_gin 
ON bulletin 
USING gin (originid gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_actor_profile_originid_gin 
ON actor_profile 
USING gin (originid gin_trgm_ops);
# Database Migrations

Bayanat uses [Alembic](https://alembic.sqlalchemy.org/) via Flask-Migrate to manage database schema changes.

## Creating a Migration

After modifying a SQLAlchemy model, generate a migration:

```bash
uv run flask db migrate -m "add status index to bulletin"
```

This auto-detects changes between your models and the database, and generates a revision file in `migrations/versions/`.

**Always review the generated file.** Alembic's autogenerate is good but not perfect. It may miss:
- Table or column renames (detected as drop + add)
- Changes to CHECK constraints
- Custom SQL functions
- Data migrations

## Manual Migrations

For changes Alembic can't auto-detect, create an empty revision and write the SQL:

```bash
uv run flask db revision -m "add custom GIN index"
```

Then edit the generated file:

```python
def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_my_index "
        "ON my_table USING gin (my_column)"
    )

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_my_index")
```

::: warning JSON in raw SQL
SQLAlchemy's `text()` parser treats `:word` as a bind parameter. If your SQL contains JSON with colons (e.g. `{"key":true}`), use `conn.exec_driver_sql()` instead of `op.execute()`:

```python
conn = op.get_bind()
conn.exec_driver_sql("INSERT INTO t (data) VALUES ('{\"key\":true}'::jsonb)")
```
:::

## Applying Migrations

```bash
uv run flask db upgrade      # apply all pending migrations
uv run flask db upgrade +1   # apply next migration only
uv run flask db downgrade -1 # roll back last migration
```

## Conventions

- Keep migrations small and focused. One logical change per revision.
- Add `IF NOT EXISTS` / `IF EXISTS` guards to DDL for idempotency.
- Define indexes in both the model (`__table_args__`) and the migration so `flask db check` shows zero drift.
- Test migrations on a copy of production data before deploying.
- Use `op.execute()` for raw SQL. Use `conn.exec_driver_sql()` only when SQL contains JSON colons.

## Fresh Installs

For new deployments, `flask create-db` builds the full schema from models. Then run:

```bash
uv run flask db upgrade
```

This stamps the baseline as applied without running it (the schema already exists).

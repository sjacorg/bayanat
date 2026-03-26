# Upgrading

## Standard Upgrade

Pull the latest code and run database migrations:

```bash
cd /bayanat
sudo -u bayanat git pull
sudo -u bayanat uv sync --frozen
sudo -u bayanat uv run flask db upgrade
sudo systemctl restart bayanat bayanat-celery
```

`flask db upgrade` is idempotent. It detects what's already applied and skips it. Safe to run multiple times.

## First-Time Alembic Upgrade

If upgrading from a version before Alembic was introduced, the process is the same:

```bash
sudo -u bayanat uv run flask db upgrade
```

The baseline migration consolidates all previous SQL migrations. It checks your database state and applies only what's missing, regardless of which version you're upgrading from.

::: tip
You no longer need to manually apply SQL files from `enferno/migrations/`. The `flask db upgrade` command handles everything automatically.
:::

## Checking Status

See which migration your database is on:

```bash
uv run flask db current
```

Check if your schema matches the models:

```bash
uv run flask db check
```

## Troubleshooting

**Migration fails partway through:**

Alembic runs inside a transaction. If a migration fails, the entire revision is rolled back. Fix the issue and run `flask db upgrade` again.

**Schema drift detected after upgrade:**

Run `flask db check`. If it reports unexpected differences, this may indicate a manual schema change that wasn't captured in a migration. Contact the development team.

# Upgrading

## Upgrading to v4

### Before You Start

1. **Back up your database:**

```bash
pg_dump <your-database-name> > bayanat-backup-$(date +%Y%m%d).sql
```

2. **Run diagnostics** from your Bayanat directory to check current health:

```bash
uv run flask doctor
```

Review the output. Fix any failures before proceeding.

::: tip
All commands below should be run from your Bayanat installation directory, as the user that owns the installation. Adapt paths and user context to match your setup.
:::

### Upgrade Steps

```bash
# 1. Pull the new code
git fetch --tags
git checkout v4.0.0

# 2. Install updated dependencies
uv sync --frozen

# 3. Run database migrations
uv run flask db upgrade

# 4. Restart your application and worker processes
```

How you restart depends on your setup:
- **systemd**: `sudo systemctl restart bayanat bayanat-celery`
- **Docker**: see [Docker Upgrade](#docker-upgrade) below
- **Other**: restart your WSGI server and Celery worker however you normally do

### Verify the Upgrade

```bash
# Run diagnostics - all checks should pass
uv run flask doctor

# Confirm migrations are current
uv run flask db current
```

Log in and verify the application works as expected.

### What Changed in v4

See the [changelog](https://github.com/sjacorg/bayanat/blob/main/CHANGELOG.md) for a full list. Key changes that affect the upgrade:

- **Database migrations now use Alembic.** The `flask db upgrade` command replaces the old manual SQL files. You no longer need to apply SQL migrations manually.
- **New dependencies.** `uv sync --frozen` installs everything needed.
- **New CLI commands.** `flask doctor` checks installation health. `flask check-db-alignment` now shows Alembic migration status.

### Troubleshooting

**`flask db upgrade` fails:**

The migration runs inside a transaction. If it fails, nothing is changed. Check the error message, fix the issue, and run `flask db upgrade` again. If you're stuck, share the error output with the development team.

**Application won't start after upgrade:**

Check your application logs. Common causes: missing dependency (re-run `uv sync --frozen`), config change needed (check `.env` against `.env-sample`).

**`flask doctor` shows warnings after upgrade:**

Warnings are non-critical. Common expected warnings:
- "No Celery workers responding" - if you haven't restarted the worker yet
- "MAIL_SERVER not configured" - if email isn't set up (optional)

Failures (shown in red) need attention before the system is fully operational.

---

## Standard Upgrade (future versions)

For routine upgrades after v4:

```bash
git pull
uv sync --frozen
uv run flask db upgrade
```

Then restart your application and worker processes.

`flask db upgrade` is idempotent - safe to run multiple times. It detects what's already applied and skips it.

## Docker Upgrade

For Docker deployments, rebuild and restart:

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

The container entrypoint runs database setup and migrations automatically on startup.

## Checking Status

See which migration your database is on:

```bash
uv run flask db current
```

Check if your schema matches the models:

```bash
uv run flask check-db-alignment
```

Run full diagnostics:

```bash
uv run flask doctor
```

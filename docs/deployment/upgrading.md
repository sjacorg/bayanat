# Upgrading

## How upgrades work

Bayanat has two upgrade mechanisms, and which one applies depends on the
version you are coming from.

| Coming from | Mechanism |
|---|---|
| v5.0.0 or later, installed with the `bayanat` installer | `sudo bayanat update` does the whole thing |
| Anything earlier | One documented manual upgrade to v5, after which updates are automatic |
| Manual or Docker deployments, any version | Documented steps, no installer involved |

Releases before v5.0.0 do not ship an `update` command at all, so there is
nothing on those hosts to run. The [Upgrading to v5](#upgrading-to-v5) section
below covers that one-time step.

::: warning Rollbacks are manual
No upgrade path rolls a database back. Alembic migrations are not reversible in
practice, so recovering from a bad upgrade means restoring the backup you took
before it, not downgrading the schema. The updater takes that backup for you
and tells you its name; keep your own as well.
:::

## Automatic updates (v5.0.0 and later)

Once you are on v5, upgrading is one command:

```bash
sudo bayanat update --check     # show current vs latest, change nothing
sudo bayanat update             # update to the latest release
sudo bayanat update v5.1.0      # or to a specific tag
```

The updater downloads the release as a signed tarball and verifies it against a
pinned key before installing anything, takes a database snapshot, runs
migrations, swaps to the new release and health-checks it. If the health check
fails it reverts to the previous release on its own.

See the [Auto-Update Runbook](/deployment/auto-update-runbook) for phases,
expected downtime, recovery states and snapshot handling, and
[Release Signing](/deployment/release-signing) for how verification works.

## Upgrading to v5

v5 changes how Bayanat is deployed, not only what it runs. Read this section
fully before starting. Depending on your deployment this is a migration with a
maintenance window, not a routine pull.

### Which path applies to you

| Your current setup | Go to |
|---|---|
| v4.x installed with the `bayanat` installer at `/opt/bayanat` | [Path A](#path-a-installer-managed-install) |
| v4.x installed manually, in your own directory with your own service units | [Path B](#path-b-manual-install) |
| v4.x on Docker Compose | [Path C](#path-c-docker) |
| v3.x, any deployment | [Upgrade to v4 first](#upgrading-to-v4), then return here |

Upgrading straight from v3 to v5 is not supported. The v4 upgrade moves you to
Alembic migrations, and v5 builds on that baseline.

### Before you start, on every path

1. **Back up the database.** Use the custom format; it restores selectively and
   compresses:

   ```bash
   pg_dump -Fc <your-database-name> > bayanat-$(date +%Y%m%d).dump
   ```

2. **Back up your configuration:** `.env`, `config.json`, and your uWSGI and web
   server configuration.

3. **Check current health** and fix any failures before upgrading:

   ```bash
   uv run flask doctor
   ```

4. **Note the migration you are on**, so you know what you are returning to:

   ```bash
   uv run flask db current
   ```

### What changes in v5

- **Service accounts split.** The web application runs as `bayanat-web` and the
  worker as `bayanat-celery`, both `nologin` system accounts in the `bayanat`
  group. The `bayanat` user remains as the deployment and database identity.
- **The release tree becomes read-only to the services.** `/opt/bayanat`,
  `releases/` and `shared/` are owned by root. Anything that wrote inside a
  release directory now writes into `shared/` instead, and `config.json` moves
  to `shared/runtime/config.json`, pointed at by `BAYANAT_CONFIG_FILE` in
  `.env`.
- **PostgreSQL local authentication changes** to peer authentication with an
  ident map. The previous permissive rule for the application role is removed;
  only the deployment user and the two service accounts can connect as it over
  the local socket.
- **Redis requires a password.** `requirepass` is set in `redis.conf` and
  `REDIS_PASSWORD` in `.env`.
- **The uWSGI socket moves** to `/run/bayanat/bayanat.sock`. Update your web
  server configuration if you manage it yourself. Installs that predate this
  keep working through a fallback to the in-release socket.
- **Releases are verified before installation.** The installer downloads a
  signed tarball and checks it against a pinned key instead of cloning over
  the network.
- **Docker: PostgreSQL moves from 15 to 16**, which requires dumping and
  restoring the database volume, and the Redis data volume path changes.
- **OCR raw payloads are no longer stored** and the text-map overlay is removed.

### Path A: installer-managed install

Three steps: put the v5 CLI in place, update the code, then apply the v5 layout.
In that order.

#### A1. Install the v5 CLI

Your current CLI has no `update` command, so install the v5 one once. Verify the
signed release first, and take the script from the tree you verified rather than
downloading it separately:

```bash
TAG=v5.0.0
cd /tmp
curl -fsSLO "https://github.com/sjacorg/bayanat/releases/download/$TAG/bayanat-$TAG.tar.gz"
curl -fsSLO "https://github.com/sjacorg/bayanat/releases/download/$TAG/bayanat-$TAG.tar.gz.minisig"
minisign -Vm "bayanat-$TAG.tar.gz" -P RWS7XvDVF0InHWTCh/86K8sXGcHU/PmzCl4uH9GUDjNnNzHhcX1BvGqZ
tar -xzf "bayanat-$TAG.tar.gz" "bayanat-$TAG/bayanat"
sudo install -m 0755 -o root -g root "bayanat-$TAG/bayanat" /usr/local/bin/bayanat
```

If `minisign` is not installed, `sudo apt-get install -y minisign` first. A
failed verification means the download is not the published release: stop, do
not install it.

This is a one-time step. After the first successful update the CLI refreshes
itself from the deployed release.

#### A2. Update the code

```bash
sudo bayanat update --check     # confirm what you are moving to
sudo bayanat update v5.0.0
```

This takes a database snapshot, fetches and verifies the release, installs
dependencies, runs `flask db upgrade`, relocates `config.json` into
`shared/runtime/`, swaps the `current` symlink and restarts the services behind
a health check.

Verify:

```bash
sudo bayanat status
sudo -u bayanat /opt/bayanat/current/.venv/bin/flask doctor
```

::: warning If the update fails on the way to v5
Because your previous release predates the health endpoint, the updater will not
start it again against a database that has already been migrated. It reverts the
symlink, leaves the services stopped, and prints the snapshot to restore. That is
deliberate: an old release running against a new schema is worse than being down.
Recover with `sudo bayanat restore <snapshot>`, which is also listed by
`sudo bayanat snapshots`.
:::

#### A3. Apply the v5 layout

Hardening is a separate command and deliberately not part of `update`: it
rewrites PostgreSQL and Redis configuration, the service units and the web
server configuration, and a code update must never be able to leave those
half-written.

```bash
sudo bayanat harden
```

It stops the services and confirms they stopped, backs up every file it will
touch (recording ownership and mode, unit enablement state, and the exact
statements needed to undo the database grant changes), applies the layout, then
health-checks the application. **If that check fails it puts every file back and
restarts the services**, leaving you on the working pre-harden configuration.
The backup directory is printed either way.

Run it **after** the update, never before. The hardened layout runs the
application as a separate account, and only v5 names the database role in its
connection string; on an older release every query would fail. `harden` checks
for this and refuses to start if the active release is too old.

Verify:

```bash
sudo bayanat status      # Layout: hardened
```

::: danger Do not re-run the installer
`bayanat install` provisions a new machine. It is not a repair or an upgrade,
and it refuses to run over an existing install. Use `bayanat update` to change
version and `bayanat harden` to apply the layout.
:::

Re-running `harden` on an already hardened install does nothing. `harden --force`
re-applies it, preserving the existing Redis password and database rule.

### Path B: manual install

For installs that do not use `/opt/bayanat`, with your own directory, service
units and web server.

```bash
# From your installation directory, as the user that owns it
git fetch --tags
git checkout v5.0.0
uv sync --frozen
uv run flask db upgrade
```

Restart the application and worker as you normally do, then verify with
`flask doctor` and `flask db current`.

`bayanat harden` assumes the installer's layout, so it does not apply here. What
it does is the reference for doing the equivalent by hand: separate web and
worker accounts sharing one group, a root-owned release tree with every
app-written path redirected outside it, peer authentication with an ident map
admitting both accounts, a Redis password, service sandboxing, and the socket in
`/run/bayanat/`.

Two things to carry over even if you keep a single service account:

- Your `.env` needs explicit `POSTGRES_USER`, `POSTGRES_DB` and `POSTGRES_HOST`.
  Leave `POSTGRES_PASSWORD` empty to keep socket authentication.
- Any app-written directory still inside the release tree has to move out before
  you make that tree read-only.

### Path C: Docker

The PostgreSQL major version moves from 15 to 16. **A PostgreSQL data directory
is not compatible across major versions.** Pulling the new image without
migrating the volume leaves the container failing to start. Dump before you pull.

```bash
# 1. With the old stack still running, dump the database
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc bayanat > bayanat-pre-v5.dump

# 2. Stop the stack
docker compose down

# 3. Remove the old database volume (you have the dump; do not skip step 1)
docker volume rm <project>_postgres_data

# 4. Pull the new code and images
git fetch --tags && git checkout v5.0.0
docker compose pull && docker compose build

# 5. Start PostgreSQL alone and let it initialize an empty cluster
docker compose up -d postgres
docker compose exec postgres pg_isready

# 6. Restore
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d bayanat --no-owner < bayanat-pre-v5.dump

# 7. Bring up the rest; the entrypoint runs migrations
docker compose up -d
docker compose logs -f bayanat
```

Also note:

- The Redis data volume path changes. Redis holds sessions and queued tasks
  rather than durable data, so the simplest path is to let the old volume go
  and start clean. Users will need to log in again.
- Images are pinned by digest and run as non-root.
- `REDIS_PASSWORD` must be set in your `.env`.

See [Docker Deployment](/deployment/docker#upgrading) for verification and rollback steps, and the rest of that page for the full guide.

### After upgrading, on every path

**Confirm the schema:**

```bash
uv run flask db current
uv run flask check-db-alignment
uv run flask doctor
```

**Clear historical OCR payloads.** v5 no longer stores raw provider output. Old
rows keep theirs until purged, and on large installs this reclaims significant
space:

```bash
uv run flask ocr purge-raw --dry-run
uv run flask ocr purge-raw
```

**Review new settings.** All are optional and have defaults; see
[Configuration](/deployment/configuration) for the full reference. The ones
most likely to matter after this upgrade are `SEARCH_TIMEOUT` and
`BACKGROUND_SEARCH_TIME_LIMIT`, the login throttles and `SESSION_LIFETIME`, and
`BAYANAT_CONFIG_FILE` if you deploy releases as read-only trees.

**Log in and check** the dashboard footer, which shows the running version.

## Rolling back

Rolling back is manual on every path, because migrations cannot be reversed.
Restore the backup taken before the upgrade and return the code to the previous
tag.

**Installer-managed:**

```bash
sudo bayanat snapshots                 # find the pre-update snapshot
sudo bayanat restore <snapshot-name>   # restores the database
sudo bayanat update <previous-tag>     # returns the code
```

For a rollback off v5 to an older major version, restore the snapshot and then
put the previous release back by hand: the older CLI has no `update` command.

**Manual install:** check out the previous tag, run `uv sync --frozen`, and
restore your dump with `pg_restore`.

**Docker:** check out the previous tag and restore your dump into a matching
PostgreSQL major version.

---

## Upgrading to v4

### Before you start

1. **Back up your database:**

```bash
pg_dump -Fc <your-database-name> > bayanat-backup-$(date +%Y%m%d).dump
```

2. **Run diagnostics** from your Bayanat directory to check current health:

```bash
uv run flask doctor
```

Review the output. Fix any failures before proceeding.

::: tip
Run the commands below from your Bayanat installation directory, as the user
that owns the installation. Adapt paths and user context to match your setup.
:::

### Upgrade steps

```bash
# 1. Get the new code
git fetch --tags
git checkout v4.0.2

# 2. Install updated dependencies
uv sync --frozen

# 3. Run database migrations
uv run flask db upgrade

# 4. Restart your application and worker processes
```

How you restart depends on your setup:

- **systemd**: `sudo systemctl restart bayanat bayanat-celery`
- **Docker**: see [Path C](#path-c-docker) above
- **Other**: restart your WSGI server and Celery worker however you normally do

### Verify

```bash
uv run flask doctor
uv run flask db current
```

Log in and verify the application works as expected.

### What changed in v4

See the [changelog](https://github.com/sjacorg/bayanat/blob/main/CHANGELOG.md)
for the full list. Key changes that affect the upgrade:

- **Database migrations use Alembic.** `flask db upgrade` replaces the old
  manual SQL files.
- **New dependencies.** `uv sync --frozen` installs everything needed.
- **New CLI commands.** `flask doctor` checks installation health;
  `flask check-db-alignment` shows migration status.

---

## Checking status

See which migration your database is on:

```bash
uv run flask db current
```

Check whether your schema matches the models:

```bash
uv run flask check-db-alignment
```

Run full diagnostics:

```bash
uv run flask doctor
```

## Troubleshooting

**`flask db upgrade` fails.** Migrations run in a transaction, so a failure
changes nothing. Fix the reported cause and run it again. If it reports multiple
heads, stop: a merge revision is missing, and applying it blind will diverge the
schema.

**Services fail to start after hardening.** Almost always a path that the
sandboxing does not allow writes to. Check `journalctl -u bayanat -n 50` for a
read-only filesystem error, then either allow that path or move the write into
`shared/`.

**`FATAL: Peer authentication failed`.** The operating system user you ran as is
not in the ident map, or the rule landed below the catch-all in `pg_hba.conf`.
Order matters; the first matching line wins.

**Celery cannot reach Redis.** `REDIS_PASSWORD` in `.env` does not match
`requirepass` in `redis.conf`, or the worker was not restarted after the change.

**502 from the web server.** The socket moved to `/run/bayanat/bayanat.sock`.
Check that the service unit creates its runtime directory and that your upstream
points at the new path.

**Application will not start after an upgrade.** Check the application logs.
Common causes are a missing dependency, fixed by re-running `uv sync --frozen`,
or a configuration change, found by comparing `.env` against `.env-sample`.

**`flask doctor` shows warnings.** Warnings are non-critical. "No Celery workers
responding" before you restart the worker and "MAIL_SERVER not configured" when
email is not set up are both expected. Failures need attention.

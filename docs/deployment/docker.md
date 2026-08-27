# Docker Deployment

Docker Compose stands up the whole stack (PostgreSQL with PostGIS, Redis, the
Flask app, two Celery workers, and a Caddy edge with automatic HTTPS) from one
command, and upgrades with another. It is the quickest way to evaluate
Bayanat, and it is a reasonable choice for an organisation that already runs
containers in production.

::: tip Recommended path
For most deployments we recommend the
[native installation](/deployment/installation).
`bayanat install yourdomain.com` is a single command, it is the configuration
the project runs and tests in production, and it has operational tooling the
Docker path does not: `bayanat update` takes an automatic pre-upgrade database
snapshot, with `bayanat snapshots` and `bayanat restore` to roll back, plus
`bayanat status`.

Under Docker your rollback point is the dump you take yourself before an
upgrade, as described below.
:::

Docker is the better fit when your organisation standardises on containers,
when you want PostgreSQL and Redis managed for you, or when you are trying
Bayanat out and want to remove it cleanly afterwards.

## Requirements

- A Linux host with Docker Engine and the Compose v2 plugin (`docker compose`,
  not the legacy `docker-compose` binary)
- 8 GB RAM minimum, 4 CPU cores, and disk sized for your media
- A domain name with an `A` record pointing at the host, if you want HTTPS
- Ports 80 and 443 reachable from the internet, so Let's Encrypt can validate
  the domain

## Install

```bash
git clone https://github.com/sjacorg/bayanat.git
cd bayanat

# Generates .env with fresh secrets and prompts for your domain
./gen-env.sh -d

docker compose up -d
```

`gen-env.sh -d` writes a `.env` containing a new `SECRET_KEY`, password salt,
TOTP secret, and random PostgreSQL and Redis passwords. It also asks for the
domain Bayanat will be served on. Supply one and Caddy requests a Let's
Encrypt certificate on first boot and the app is configured for HTTPS
(`SECURE_COOKIES` and `FORCE_HTTPS` are set to `True`). Leave it blank and the
stack serves plain HTTP on port 80, which is appropriate for local evaluation
or when you already run a TLS-terminating proxy in front of it.

You can skip the prompt with `./gen-env.sh -d -D bayanat.example.org`.

::: warning
`.env` holds every secret the deployment has. It is excluded from git. Back it
up somewhere safe: without it, an existing database is unreadable, because
password hashes and two-factor secrets are keyed to `SECURITY_PASSWORD_SALT`
and `SECURITY_TOTP_SECRETS`.
:::

The database and Redis passwords are passed to their containers as environment
variables, so anyone who can run `docker inspect` on the host can read them.
Membership of the `docker` group is equivalent to root on the host, so treat it
as such and keep it to the operators who administer this deployment.

### First Sign-in

On a fresh database the app container creates the schema and an `admin` user,
then prints a one-time random password to its logs:

```bash
docker compose logs bayanat | grep "Generated password"
```

Sign in at your domain with `admin` and that password. The setup wizard runs
after first login. Change the password from your account settings afterwards.

Record the password before you recreate the container. It is printed once, to
that container's log, and `docker compose up -d --force-recreate` replaces the
container and discards it.

If the admin account was deleted, recreate it:

```bash
docker compose exec bayanat flask install -u admin
```

That command refuses to act when an admin already exists. To set a new
password for an existing account, reset it instead:

```bash
docker compose exec bayanat flask reset -u admin
```

It prompts for the new password twice and enforces the password policy.

## What Runs

| Service | Purpose |
|---------|---------|
| `caddy` | TLS termination, static files, reverse proxy. Ports 80 and 443 |
| `bayanat` | uWSGI application server |
| `celery` | Default queue worker, plus the beat scheduler |
| `celery-ocr` | Dedicated OCR queue worker |
| `postgres` | PostgreSQL 16 with PostGIS |
| `redis` | Celery broker and session store |

Every service restarts automatically unless you stop it deliberately, so the
stack comes back after a host reboot. Container logs are capped at 10 MB per
file with five files kept, so they cannot fill the disk.

Only `caddy` publishes ports. Postgres and Redis are reachable on the internal
Compose network only.

## Upgrading

::: danger Upgrading from v4 is a different procedure
This section covers routine upgrades between v5 releases. **The v4 to v5 hop is
not a routine upgrade:** PostgreSQL moves from 15 to 16, and a PostgreSQL data
directory is not compatible across major versions. Following the steps below
from a v4 stack leaves PostgreSQL 16 starting against a version 15 data
directory, and it will not come up.

Use the migration in [Upgrading](/deployment/upgrading) instead, which dumps the
database, removes the old volume, and restores into a freshly initialized one.
:::

The container entrypoint runs `flask db upgrade` on every start, so upgrading
between v5 releases is: back up, pull, rebuild, restart.

**Always take a database dump first.** Migrations are not reversible.

```bash
cd bayanat

# 1. Back up the database and your secrets. Note the filename; the rollback
#    steps below need this exact path.
docker compose exec -T postgres pg_dump -Fc -U bayanat bayanat \
  > ~/bayanat-$(date +%F).dump
cp .env ~/bayanat-env-$(date +%F).bak

# 2. Fetch the release you want
git fetch --tags
git checkout v5.0.1

# 3. Rebuild the images
docker compose build

# 4. Restart. Migrations run automatically as the app container starts.
docker compose up -d
```

Watch the app come up and confirm the migration ran:

```bash
docker compose logs -f bayanat
```

Then verify:

```bash
docker compose exec bayanat flask doctor
docker compose exec bayanat flask db current
```

`flask doctor` checks the database, PostGIS, `pg_trgm`, pending migrations,
schema alignment, Redis, Celery, the filesystem, and config. Every check
should pass. Sign in and confirm the application behaves as expected.

::: tip
`docker compose up -d` only recreates containers whose image or configuration
changed. There is no need to `down` the stack first, and doing so takes the
site offline for the whole rebuild rather than just the restart.
:::

### Rolling Back

If an upgrade goes wrong, return to the previous tag and restore the dump.
The schema must match the code, so restoring the database alone is not enough.

The application and workers must be stopped for the restore. If they are
running, they hold connections that make `dropdb` fail, and the old code would
run migrations against the database while it is being replaced.

```bash
# 1. Stop everything that touches the database. Leave postgres running.
docker compose stop bayanat celery celery-ocr

# 2. Restore into a clean database. Use the dump you took before the upgrade.
BACKUP=~/bayanat-2026-08-16.dump
docker compose exec -T postgres dropdb -U bayanat bayanat
docker compose exec -T postgres createdb -U bayanat bayanat
docker compose exec -T postgres pg_restore -U bayanat -d bayanat < "$BACKUP"

# 3. Go back to the previous release and start again
git checkout v5.0.0
docker compose build
docker compose up -d
```

Unlike the native installer, the Docker path does not take automatic
pre-upgrade snapshots. The dump in step 1 above is your only rollback point,
so do not skip it.

## Backups

Bayanat can take scheduled database backups itself, locally or to S3. Set
`BACKUPS=1` and the related variables in `.env`; see
[Configuration](/deployment/configuration). They are written to `./backups`
on the host.

Media files live on the host at the path in `MEDIA_PATH` (default
`./enferno/media`) and are not covered by database backups. Back them up
separately.

What a full restore needs, beyond the database dump:

- `.env`, or the database is unreadable
- `config.json`
- the media directory

Certificates in the `caddy_data` volume do not need backing up: Caddy reissues
them on a new host. Do not delete that volume casually on a working host,
though, because repeated reissuance runs into Let's Encrypt rate limits.

A manual dump at any time:

```bash
docker compose exec -T postgres pg_dump -Fc -U bayanat bayanat > backup.dump
```

## Operations

```bash
# Status of every service, including health
docker compose ps

# Follow logs
docker compose logs -f bayanat
docker compose logs -f celery

# Restart after a config.json change
docker compose restart bayanat celery celery-ocr

# Flask CLI
docker compose exec bayanat flask doctor

# Database shell
docker compose exec postgres psql -U bayanat bayanat
```

### Stopping and Removing

```bash
# Stop the stack. Data is kept, `up -d` brings it back as it was.
docker compose down
```

To remove an evaluation completely, delete the volumes as well:

```bash
docker compose down -v
```

::: danger
`down -v` destroys the database, the Redis data and the issued certificates.
There is no undo. Take a dump first if there is anything in the deployment you
want to keep.
:::

Media is not stored in a volume. It stays on the host at `MEDIA_PATH`
(default `./enferno/media`) and must be deleted separately.

## Configuration

Three sources, in the order Bayanat merges them:

1. `.env` on the host, mounted read-only into the app and worker containers.
   Secrets and infrastructure settings.
2. `config.json` on the host, mounted read-write. Feature toggles, mail, media
   and map settings, editable from the System Administration dashboard.
3. Hardcoded defaults in `enferno/settings.py`.

::: warning Applying a change to `.env`
After editing `.env`, run:

```bash
docker compose up -d --force-recreate bayanat celery celery-ocr
```

Plain `docker compose up -d` is not enough, and neither is `restart`. Both
files are mounted individually rather than as a directory, and most editors
(and `sed -i`) save by writing a new file and renaming it over the old one.
The container stays attached to the original file, so it keeps reading the
old settings, silently, until it is recreated. Editing in place with
`nano` avoids this, but recreating is the reliable habit.

The same applies to `config.json` when you edit it on the host. Changes made
through the System Administration dashboard are written by the application
itself and only need a restart of `bayanat` and the workers.
:::

Tuning knobs specific to this deployment, all optional in `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DOMAIN` | `:80` | Caddy site address. A hostname enables automatic HTTPS |
| `MEDIA_PATH` | `./enferno/media` | Host path for uploaded media |
| `UWSGI_PROCESSES` | `4` | Application worker processes |
| `UWSGI_THREADS` | `2` | Threads per worker |
| `UWSGI_HARAKIRI` | `300` | Seconds before a stuck request is killed |

`UWSGI_HARAKIRI` must outlast your slowest upload. Request bodies are streamed
rather than buffered, so a worker is occupied for the whole duration of a media
upload, and harakiri cannot tell a slow upload from a hung request. Five
minutes covers a 1 GB file at roughly 30 Mbit/s. Raise it if your users upload
large media over slower links.

### Behind an Existing Proxy

If you already terminate TLS elsewhere, leave `DOMAIN` blank so Caddy serves
HTTP on port 80, and point your proxy at it. In `.env`, set:

```
SECURE_COOKIES=True
FORCE_HTTPS=False
```

`SECURE_COOKIES=True` is correct because users still reach the site over
HTTPS, so the session cookie must be marked secure.

::: danger
Do not set `FORCE_HTTPS=True` in this arrangement. It makes the app redirect
any request whose `X-Forwarded-Proto` is not `https`, and Caddy sets that
header from the connection it received, which is plain HTTP from your proxy.
The result is an infinite redirect loop and a completely unreachable site.
:::

Your outer proxy is responsible for redirecting HTTP to HTTPS and for sending
the `Strict-Transport-Security` header, which is where that belongs when it
owns the certificate.

## Development and Testing

These are not production configurations.

```bash
# Development stack, app exposed on 127.0.0.1:5000, no edge
docker compose -f docker-compose-dev.yml up

# Test suite
docker compose -f docker-compose-test.yml up
```

## Troubleshooting

**Caddy will not issue a certificate.** Let's Encrypt must reach the host on
port 80 to validate. Confirm the `A` record resolves to the host and that no
firewall blocks 80 or 443, then check `docker compose logs caddy`.

**`bayanat` restarts in a loop with `PermissionError: '/app/logs/bayanat.log'`.**
The containers run as uid 1000, and on Linux a bind mount keeps the host's
ownership, so directories owned by root are not writable by the application.
`gen-env.sh -d` sets this up for you; if you created the directories by hand,
or copied the deployment from elsewhere, fix the ownership and restart:

```bash
sudo chown -R 1000 logs backups enferno/imports enferno/media config.json
docker compose up -d
```

Docker Desktop on macOS remaps ownership and hides this, so a deployment that
works on a developer laptop can still fail on a Linux server.

**`bayanat` never becomes healthy.** Its health check calls `/health`, which
touches both PostgreSQL and Redis. Check `docker compose logs bayanat` for
connection errors, and confirm `POSTGRES_PASSWORD` and `REDIS_PASSWORD` in
`.env` match what the database and Redis containers were created with. If you
changed them after first boot, the existing volumes still hold the old
credentials.

**Caddy does not start.** It waits for `bayanat` to report healthy, so that
users see no gateway errors during a restart. Fix the app first.

**Uploads fail after a few minutes.** harakiri killed the request. Raise
`UWSGI_HARAKIRI` in `.env` and run `docker compose up -d`. The
`harakiri without post buffering` warning in the app logs at startup is
expected and explains the same trade-off.

**Everything is slow on an ARM host.** The PostGIS image is published for
amd64 only and runs under emulation on Apple Silicon and ARM servers. This is
fine for evaluation and unsuitable for production; deploy on x86_64.

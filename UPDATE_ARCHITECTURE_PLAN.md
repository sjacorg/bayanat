# Bayanat Install & Update Architecture Plan

## Context

Bayanat is a human rights documentation tool used by non-technical partners. They install via `curl | sh` and manage updates from the admin web UI. They do not SSH into servers. The system must be self-updating, secure, and dead simple.

## The Core Problem

The current update system (on `automatic-updates` branch) lives **inside** the app it's updating. This creates:
- Circular dependencies (app must be running to update itself, but updates can break the app)
- Complex state management (Redis distributed locks, Celery background tasks, socket APIs, maintenance mode)
- A two-user security model (bayanat + bayanat-daemon) with a custom socket API just to restart services
- Scheduling/grace period logic that adds edge cases without real value

## The Fix: External Bash CLI + Symlink Releases + Web Trigger

Split the concern cleanly:
- **Bash CLI** (`/usr/local/bin/bayanat`) handles all system operations: install, update, rollback, restart
- **Flask app** only triggers the CLI and displays status
- **Symlink releases** for atomic version switching and instant rollback

The app never updates itself. It fires off a detached process and gets out of the way.

---

## Branch Strategy

**Start fresh from `main`.** Do not merge the `automatic-updates` branch.

- `automatic-updates` branch is kept as **reference only** (borrow patterns, not code)
- New branch: `bayanat-cli` (off `main`)
- Cherry-pick `ec151683c` (SQL migration tracking system) as the foundation, it's clean and standalone
- Build the new CLI system on top of main + migration tracking

Why: the old branch has ~20 diverged commits full of Celery tasks, Redis locks, socket APIs, and scheduling that we're explicitly removing. Merging it means resolving conflicts in code we're deleting. Starting clean avoids that entirely.

### Cherry-pick: Migration Tracking System (`ec151683c`)

This commit adds the core DB migration infrastructure that both the installer and updater depend on:
- `MigrationHistory` model (tracks which `.sql` files have been applied)
- `enferno/utils/migration_utils.py` (runner: applies pending SQL in filename order, each in own transaction)
- `flask apply-migrations` + `flask create-migration` CLI commands
- Makes existing migrations idempotent (IF EXISTS, EXCEPTION guards)
- `db_alignment_helpers.py` additions for dynamic field column checks

This is standalone, well-tested, and doesn't pull in any update system complexity.

---

## Target Directory Layout

```
/opt/bayanat/
  current -> releases/3.1.0/          # Atomic symlink, services point here
  releases/
    3.1.0/                             # Immutable release (code + .venv)
      .env -> /opt/bayanat/shared/.env # Symlink to shared config
      enferno/
        media -> /opt/bayanat/shared/media  # Symlink to shared media
      config.json                      # Written by app, lives in release dir
      bayanat.sock                     # uWSGI socket (created at runtime)
      reload.ini                       # Touch this to trigger uWSGI reload
      uwsgi.ini                        # uWSGI config (part of repo)
      .venv/                           # Python virtualenv for this release
    3.0.0/                             # Previous release, kept for rollback
  shared/
    .env                               # Environment secrets (persists across updates)
    media/                             # User uploads (persists across updates)
    backups/                           # DB backups before each update
  system/                              # Reserved for generated system configs
  logs/
    update.log                         # CLI writes structured update logs
```

### What lives where

| Location | Persists across updates? | Who writes it? |
|---|---|---|
| `shared/.env` | Yes | Installer generates once, admin edits manually |
| `shared/media/` | Yes | App writes during normal use |
| `shared/backups/` | Yes | CLI writes before each update |
| `releases/<ver>/config.json` | No (per-release) | App writes via settings dashboard |
| `releases/<ver>/.venv/` | No (per-release) | `uv sync` during install/update |
| `releases/<ver>/bayanat.sock` | No (runtime) | uWSGI creates at startup |
| `/etc/systemd/system/bayanat.service` | Yes | Installer generates, points at `current/` |
| `/etc/caddy/Caddyfile` | Yes | Installer generates |
| `/etc/sudoers.d/bayanat` | Yes | Installer generates |

### config.json handling during updates

`config.json` is written by the app (settings dashboard) and lives in the release directory. During updates, the CLI copies `config.json` from the old release to the new one before swapping the symlink.

---

## Service Restart Strategy

Three scenarios require restarting services from within the app:

### 1. Config change from settings dashboard (uWSGI + Celery)

**uWSGI:** Touch-reload via `reload.ini`. uWSGI watches this file and does a graceful reload. Caddy stays up (proxies to unix socket), so the frontend sees 502 briefly then reconnects. Reload takes ~5 seconds.

**Celery:** `sudo systemctl restart bayanat-celery` via sudoers entry. The app calls this from the reload endpoint.

**Dev mode:** `import uwsgi` fails, app returns "please restart manually" message. No silent failures.

### 2. System update (full restart via CLI)

The bash CLI runs `systemctl restart bayanat bayanat-celery` directly (runs as root via sudo). No app involvement needed.

### 3. Dev mode (flask run)

No uWSGI, no systemd. Reload endpoint detects this and tells the user to restart manually.

### Sudoers entries

```
bayanat ALL=(root) NOPASSWD: /usr/local/bin/bayanat update
bayanat ALL=(root) NOPASSWD: /usr/local/bin/bayanat status
bayanat ALL=(root) NOPASSWD: /usr/bin/systemctl restart bayanat-celery
```

### uWSGI config (uwsgi.ini)

```ini
[uwsgi]
virtualenv=.venv
module=run:app
master=true
processes=1
threads=2
http-socket=/opt/bayanat/current/bayanat.sock
chmod-socket=660
vacuum=true
touch-reload=reload.ini
reload-mercy=5
worker-reload-mercy=3
```

Key settings:
- `http-socket` (not `http`): unix socket so Caddy can proxy. Caddy stays up during reloads.
- `touch-reload=reload.ini`: app touches this file to trigger graceful reload, no signals needed.
- `reload-mercy=5`: kill workers after 5s if they don't finish (web requests should be <1s, long work runs in Celery).

---

## How Web-Triggered Updates Work

```
Admin clicks "Update" in UI
        |
        v
Flask: enable maintenance mode, log out users
Flask: spawn `sudo /usr/local/bin/bayanat update` (detached via setsid/nohup)
Flask: return "Update started" (user sees maintenance page with auto-refresh)
        |
        v  (runs independently of the app)
CLI: backup DB
CLI: clone new release into releases/<new>/
CLI: create venv, uv sync
CLI: symlink shared resources (.env, media/)
CLI: copy config.json from old release to new
CLI: run SQL migrations (via flask apply-migrations)
CLI: atomic symlink swap (current -> new)
CLI: systemctl restart bayanat bayanat-celery
CLI: health check (curl unix socket + flask check-db-alignment)
CLI: if health check fails -> rollback (swap symlink back, restore DB, restart)
CLI: write update result to update.log + DB
CLI: clear maintenance mode
        |
        v
App comes back on new version. Admin sees success on refresh.
```

## Security Model

Sudoers entries replace the entire daemon + socket API + handler script:

```
bayanat ALL=(root) NOPASSWD: /usr/local/bin/bayanat update
bayanat ALL=(root) NOPASSWD: /usr/local/bin/bayanat status
bayanat ALL=(root) NOPASSWD: /usr/bin/systemctl restart bayanat-celery
```

- `bayanat` user runs the app. Minimal sudo (three commands only). No access outside `/opt/bayanat/`.
- The CLI script is owned by root (`root:root`, mode `755`), not writable by the app user. Tamper-proof.
- Caddy user added to `bayanat` group to read the unix socket.
- No daemon user, no socket API, no handler script.
- This is **stronger** than the current two-user model with less attack surface.

---

## Key Principles

- **Releases are immutable.** No in-place `git pull`. Each version is a fresh directory.
- **`current` symlink is the single source of truth** for which version is running.
- **`shared/` persists across updates.** Secrets, uploads, backups never move.
- **Rollback = swap symlink + restore DB.** Instant, no rebuild.
- **Bash CLI does system work.** No Python/Node dependency for the management tool.
- **App only triggers and displays.** Flask never touches git, systemd, or its own process lifecycle.
- **Fail-safe defaults.** Auto-backup before update, auto-rollback on failure, health checks after restart.
- **Dev mode is honest.** No fake reloads, just "please restart manually."

---

## What Gets Killed (vs `automatic-updates` branch)

| Component | Why it existed | Why it's gone |
|---|---|---|
| `enferno/tasks/update.py` | Celery tasks for background updates + scheduling | Bash CLI runs detached, no Celery needed |
| `enferno/utils/update_utils.py` | Redis distributed locks + state tracking | CLI uses a simple lockfile (`/opt/bayanat/.update.lock`) |
| Socket API (`bayanat-handler.sh`, `bayanat-api.socket`, `bayanat-api@.service`) | App couldn't restart services directly | Sudoers entry, CLI restarts directly |
| `bayanat-daemon` user | Security boundary for service restarts | Sudoers is tighter and simpler |
| Scheduled updates + grace period | PM feature, rarely used | Adds edge cases, cron is simpler if needed |
| `UPDATE_GRACE_PERIOD_MINUTES` | Grace period config | Gone |
| `VERSION_CHECK_INTERVAL` | Periodic version polling via Celery | Simple check on admin page load |
| Redis update state keys | Track update progress across processes | CLI writes to log file, app reads it |
| SIGHUP reload | Unreliable, races with HTTP response | touch-reload via uWSGI (production), manual restart (dev) |

## What Stays (Simplified)

| Component | Role |
|---|---|
| Maintenance mode (file-based) | CLI enables it, app checks the file and shows maintenance page |
| `UpdateHistory` model | CLI writes a record after update, app displays history (read-only) |
| Version display in UI | Reads version from `pyproject.toml` |
| "Update available" check | Admin page calls `git ls-remote` on load (or CLI caches latest version) |
| "Update Now" button | Triggers `sudo /usr/local/bin/bayanat update` via detached subprocess |
| SQL migration tracking | `MigrationHistory` model + `migration_utils.py` + `flask apply-migrations` (cherry-picked) |
| touch-reload | uWSGI watches `reload.ini`, Caddy proxies via unix socket, seamless reload |

---

## Phased Plan

### Phase 1: Installer PR

Create `bayanat-cli` branch from `main`. Cherry-pick migration tracking. Build CLI installer.

**Done:**
- [x] Branch created, cherry-pick applied
- [x] `bayanat install` command (system deps, users, DB, clone, venv, .env, systemd, Caddy, sudoers)
- [x] Symlink-based directory layout
- [x] uWSGI unix socket + Caddy reverse proxy
- [x] touch-reload for config changes (production)
- [x] Dev mode detection (skip reload, ask user to restart)
- [x] Tested on Hetzner Ubuntu 24.04 (ARM64) with SSL via Caddy

**Remaining:**
- [ ] Add Celery restart to reload endpoint (for settings dashboard changes)
- [ ] Test idempotency edge cases
- [ ] Open PR

### Phase 2: Updater PR

Add `update`, `rollback`, and `status` subcommands to the CLI.

`bayanat update`:
1. Acquire lockfile (`/opt/bayanat/.update.lock`), fail if already locked
2. Pre-flight: disk space, DB connectivity, current version
3. Fetch latest release tag from GitHub (`git ls-remote`)
4. If already on latest, exit clean
5. Enable maintenance mode
6. Backup DB (`pg_dump -Fc` into `shared/backups/`)
7. Clone/checkout new version into `releases/<new>/`
8. Create venv, `uv sync --frozen`
9. Symlink shared resources (`.env`, `media/`)
10. Copy `config.json` from old release to new
11. Run `flask apply-migrations` (from new release's venv)
12. Atomic symlink swap: `current -> releases/<new>/`
13. Restart services (`systemctl restart bayanat bayanat-celery`)
14. Health check (curl unix socket + `flask check-db-alignment`)
15. If health check fails: swap symlink back, restore DB backup, restart, log failure
16. Clear maintenance mode
17. Write update record (version_from, version_to, status, timestamp)
18. Prune old releases (keep last 3)
19. Release lockfile

`bayanat rollback`:
1. Find previous release in `releases/`
2. Swap symlink
3. Restore most recent DB backup
4. Restart services
5. Health check

`bayanat status`:
- Current version, available version, last update result, service health (`systemctl is-active`)

### Phase 3: App Integration PR

Wire the Flask admin UI to the CLI:
- "Update Now" button: spawns `sudo /usr/local/bin/bayanat update` detached via `setsid`/`nohup`
- "Check for Updates": lightweight version check (reads cached result or calls `git ls-remote`)
- Update history page: reads from `UpdateHistory` table
- Maintenance page: auto-refresh until app comes back (borrow from old branch)
- Add `UpdateHistory` model + migration (borrow from `automatic-updates`)
- Add maintenance middleware (borrow from `automatic-updates:enferno/utils/maintenance.py`)

### Phase 4: Migration Path (optional)

For existing installs using the old flat layout:
- `bayanat migrate-layout`: reorganizes `/opt/bayanat` into the new `releases/` + `shared/` structure
- One-time operation, documented in release notes

---

## Testing Strategy

- **Test repo:** `sjacorg/bayanat-test` (public) for pushing dummy release tags
- **Test server:** Hetzner `cax11` (ARM64, Ubuntu 24.04) with real domain for SSL testing
- **Installer uses `BAYANAT_REPO` env var** to point at test repo instead of production
- Push branch code to test repo as tagged releases (e.g. `v99.0.0`)
- Clean-slate test: drop DB, rm -rf /opt/bayanat, re-run installer

---

## CLI Tool: Why Bash

| | Bash | Python | Rust |
|---|---|---|---|
| System commands | Native (git, systemctl, pg_dump, ln, uv) | subprocess wrappers | Command::new wrappers |
| Dependencies | None (sh is everywhere) | Needs Python outside app venv | Needs compile toolchain |
| Maintainability | Fine for ~300 lines of structured script | Overkill for this scope | Overkill for this scope |
| Install story | `curl \| sh` drops it in `/usr/local/bin/` | Needs pipx/uv tool install | Needs binary distribution |

Bash is the right tool. The CLI is ~300 lines of system commands with error handling. No business logic, no data structures, no concurrency.

---

## What to Borrow from `automatic-updates` (Reference)

While building on the fresh branch, use these as reference (read, adapt, don't merge):

| File | What to borrow |
|---|---|
| `install.sh` | System dep installation, Caddy config generation, systemd unit templates |
| `enferno/utils/maintenance.py` | File-based maintenance mode (lock file + middleware). Clean, bring most of it over. |
| `enferno/admin/models/UpdateHistory.py` | Model structure for update audit log |
| `enferno/migrations/20251022_000002_create_update_history.sql` | SQL for update_history table |
| `enferno/admin/templates/admin/system-update.html` | UI patterns for update page (simplify heavily) |
| `enferno/commands.py` (run_system_update) | Rollback logic patterns, health check approach |
| `smoke-test.sh` | Testing patterns for the update flow |

---

## Research References

- **Ghost CLI:** Symlink-based releases (`/current -> /versions/x.y.z/`), auto-rollback, nginx/systemd/SSL generation. Gold standard for self-hosted web app CLI.
- **Capistrano pattern:** `releases/`, `shared/`, `current` symlink. Atomic swap via `ln -s new /tmp/current && mv -T /tmp/current /path/current`.
- **Claude Code:** Self-contained binary, background update check, checksum verification, release channels.
- **Coolify/Dokku:** Docker-based self-update patterns. Simpler but adds Docker dependency.

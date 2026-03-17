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
  current -> releases/3.1.0/       # Atomic symlink swap
  releases/
    3.1.0/                          # Immutable release (code + venv)
    3.0.0/                          # Previous, kept for rollback
  shared/
    .env                            # Config (persists across versions)
    media/                          # User uploads
    backups/                        # DB backups
  system/
    caddy.conf                      # Generated, symlinked to Caddy config
    bayanat.service                 # Generated systemd unit
    bayanat-celery.service
  logs/
    update.log                      # CLI writes structured update logs
```

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
CLI: symlink shared resources
CLI: run SQL migrations (via flask apply-migrations)
CLI: atomic symlink swap (current -> new)
CLI: systemctl restart bayanat bayanat-celery
CLI: health check (HTTP ping + DB alignment)
CLI: if health check fails -> rollback (swap symlink back, restore DB, restart)
CLI: write update result to update.log + DB
CLI: clear maintenance mode
        |
        v
App comes back on new version. Admin sees success on refresh.
```

## Security Model

One sudoers line replaces the entire daemon + socket API + handler script:

```
bayanat ALL=(root) NOPASSWD: /usr/local/bin/bayanat update
```

- `bayanat` user runs the app. Zero sudo except this one command. No access outside `/opt/bayanat/`.
- The CLI runs as root (via sudo), can restart services directly.
- No daemon user, no socket API, no handler script.
- The CLI script is owned by root (`root:root`, mode `755`), not writable by the app user. Tamper-proof.
- This is **stronger** than the current two-user model with less attack surface.

---

## Key Principles

- **Releases are immutable.** No in-place `git pull`. Each version is a fresh directory.
- **`current` symlink is the single source of truth** for which version is running.
- **`shared/` persists across updates.** Config, uploads, backups never move.
- **Rollback = swap symlink + restore DB.** Instant, no rebuild.
- **Bash CLI does system work.** No Python/Node dependency for the management tool.
- **App only triggers and displays.** Flask never touches git, systemd, or its own process lifecycle.
- **Fail-safe defaults.** Auto-backup before update, auto-rollback on failure, health checks after restart.

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

## What Stays (Simplified)

| Component | Role |
|---|---|
| Maintenance mode (file-based) | CLI enables it, app checks the file and shows maintenance page |
| `UpdateHistory` model | CLI writes a record after update, app displays history (read-only) |
| Version display in UI | Reads version from `pyproject.toml` |
| "Update available" check | Admin page calls `git ls-remote` on load (or CLI caches latest version) |
| "Update Now" button | Triggers `sudo /usr/local/bin/bayanat update` via detached subprocess |
| SQL migration tracking | `MigrationHistory` model + `migration_utils.py` + `flask apply-migrations` (cherry-picked) |

---

## Phased Plan

### Phase 1: Foundation (PR 1)

Create `bayanat-cli` branch from `main`. Cherry-pick the migration tracking system.

```
git checkout main
git pull
git checkout -b bayanat-cli
git cherry-pick ec151683c    # SQL migration tracking system
```

Resolve any conflicts (should be minimal since the commit is self-contained).

### Phase 2: Installer (PR 2)

Build `/usr/local/bin/bayanat` bash CLI with the `install` subcommand.

`bayanat install`:
1. Install system deps (postgres, redis, caddy, ffmpeg, uv, etc.)
2. Create `bayanat` user + directory structure (`/opt/bayanat/{releases,shared,system,logs}`)
3. Configure sudoers entry for `bayanat` user
4. Clone repo, checkout latest release tag into `releases/<version>/`
5. Create venv in release dir, `uv sync --frozen`
6. Generate `.env` into `shared/`, symlink into release
7. Run `flask create-db --create-exts && flask import-data`
8. Run `flask apply-migrations` (idempotent, safe on fresh install)
9. Generate + install systemd units (pointing at `/opt/bayanat/current/`)
10. Generate + install Caddy config (SSL or localhost)
11. Set `current` symlink, start services
12. Health check (HTTP ping)

Entry point: `curl -sL https://get.bayanat.org | sudo bash` (or repo raw URL).

Reference: borrow from `automatic-updates:install.sh` for system dep installation and service generation patterns.

### Phase 3: Updater (PR 3)

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
10. Run `flask apply-migrations` (from new release's venv)
11. Atomic symlink swap: `current -> releases/<new>/`
12. Restart services (`systemctl restart bayanat bayanat-celery`)
13. Health check (HTTP GET + `flask check-db-alignment`)
14. If health check fails: swap symlink back, restore DB backup, restart, log failure
15. Clear maintenance mode
16. Write update record (version_from, version_to, status, timestamp)
17. Prune old releases (keep last 3)
18. Release lockfile

`bayanat rollback`:
1. Find previous release in `releases/`
2. Swap symlink
3. Restore most recent DB backup
4. Restart services
5. Health check

`bayanat status`:
- Current version, available version, last update result, service health (`systemctl is-active`)

### Phase 4: App Integration (PR 4)

Wire the Flask admin UI to the CLI:
- "Update Now" button: spawns `sudo /usr/local/bin/bayanat update` detached via `setsid`/`nohup`
- "Check for Updates": lightweight version check (reads cached result or calls `git ls-remote`)
- Update history page: reads from `UpdateHistory` table
- Maintenance page: auto-refresh until app comes back (already exists, can borrow from old branch)
- Add `UpdateHistory` model + migration (borrow from `automatic-updates`)
- Add maintenance middleware (borrow from `automatic-updates:enferno/utils/maintenance.py`)

### Phase 5: Migration Path (PR 5, optional)

For existing installs using the old flat layout:
- `bayanat migrate-layout`: reorganizes `/opt/bayanat` into the new `releases/` + `shared/` structure
- One-time operation, documented in release notes

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
| `install.sh` | System dep installation, Caddy config generation, systemd unit templates, uWSGI setup |
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

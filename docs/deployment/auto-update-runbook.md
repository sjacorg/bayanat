# Bayanat Auto-Update Runbook

Short operator reference for the `bayanat update` flow. Design notes live
in the development spec (not shipped with the repo).

## Triggering an update

- **One-click from UI:** an admin-role user clicks "Update now" from the
  "Update available: X.Y.Z" banner in the nav bar.
- **From the shell (as root):** `sudo bayanat update [<tag>]`
  (defaults to the latest GitHub release). The CLI requires root to stop
  / start services, write `/opt/bayanat`, and take snapshots.
- **Check only (no changes, no root):** `sudo -u bayanat bayanat update --check`.

The update runs as `bayanat-update.service`, a transient systemd unit
that outlives Flask restarts, SSH disconnects, and browser closes. Tail
live logs with:

```
sudo journalctl -u bayanat-update -f
```

## Opt-in auto-apply for patch releases

In the admin UI under System Administration, toggle "Auto-apply patch
releases" on. With the toggle on, any bump within the same minor line
(e.g. `4.1.0` to `4.1.1`) installs silently every 6 hours via the same
pipeline. Minor and major bumps (e.g. `4.1.x` to `4.2.0`) always notify
and wait for a manual click.

## Expected timing

| Phase | Duration | Production impact |
|---|---|---|
| PREPARE (fetch + deps) | 1-5 min | None, old version serves traffic |
| Stop services | ~3 s | 502 from Caddy begins |
| Snapshot (`pg_dump -Fc`) | 10-60 s | 502 |
| Migrate (`flask db upgrade`) | 1-30 s | 502 |
| Swap + start services | ~5 s | 502 |
| Verify (health probe) | 1-10 s | New version serving |
| **Total visible downtime** | **~30-90 s** | |

Caddy returns `502 Bad Gateway` during the maintenance window. Browsers
retry automatically; partners see a brief "service unavailable" view.

## If something goes wrong

### Migration failed (Alembic transaction rolled back)

Nothing to do. Services restart on the previous release automatically.
The UI shows the `error` field. Report the broken release; the previous
version keeps running.

### Health probe failed after swap (auto-rollback succeeded)

Nothing to do. The updater reverted the symlink and restarted on the
previous release. The pre-update snapshot is retained at
`/opt/bayanat/shared/backups/`.

### NEEDS_INTERVENTION

This state only happens when two independent failures compound: the new
release was broken AND rolling back did not reach a healthy state. The
maintenance flag stays up so users see a 502 instead of raw errors.
Recover:

```
sudo -u bayanat bayanat status            # read-only; confirm state
sudo bayanat snapshots                    # list snapshots (needs root)
sudo bayanat restore pre-<ts>.dump        # restores DB (needs root)
sudo systemctl start bayanat bayanat-celery
```

Then file a bug with journal logs from `journalctl -u bayanat-update`.

### Stuck state (process died, state file orphaned)

```
sudo bayanat update --recover
```

## Snapshots

- Location: `/opt/bayanat/shared/backups/pre-*.dump`
- Format: `pg_dump -Fc` (PostgreSQL custom format)
- Retention: last 5 snapshots OR last 30 days, whichever is greater
- Override retention: `export BAYANAT_SNAPSHOT_RETENTION_DAYS=60`
- List: `sudo bayanat snapshots` or visit `/admin/snapshots/` in the UI
  (read-only)
- Restore: `sudo bayanat restore <name>` (prompts for confirmation;
  stops services; pipes through `pg_restore --clean --if-exists`;
  restarts services). Requires root. Not available from the web UI by
  design.

## Files

| Path | Purpose |
|---|---|
| `/usr/local/bin/bayanat` | The CLI script |
| `/usr/local/sbin/bayanat-start-update` | Root wrapper the UI invokes via sudo |
| `/etc/sudoers.d/bayanat` | Granted commands for the `bayanat` user |
| `/opt/bayanat/state/update.json` | Current update state (sanitized JSON) |
| `/opt/bayanat/state/update.lock` | PID lock file |
| `/opt/bayanat/shared/backups/` | Pre-update snapshots |
| `/health` (Flask endpoint) | 200 = DB + Redis reachable |

## Admin UI surface

- Nav-bar banner chip: shows when `latest != current`
- Progress dialog: polls `/admin/api/updates/status` every 2 s during an
  active update
- Settings toggle: System Administration -> "Auto-apply patch releases"
- Snapshots page: `/admin/snapshots/` (read-only list; restore stays on
  the CLI)

## Manual CLI reference

Commands marked `(root)` require `sudo bayanat ...`; the others can run
as the app user via `sudo -u bayanat bayanat ...`.

```
bayanat update [<tag>]       (root)  default: latest GitHub release
bayanat update --check               show current vs latest; no changes
bayanat update --recover     (root)  recover a stuck state file
bayanat snapshots            (root)  list pre-update snapshots
bayanat restore <name>       (root)  interactive restore from a snapshot
bayanat status                       version + services + update state
```

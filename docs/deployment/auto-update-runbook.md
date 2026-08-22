# Bayanat Auto-Update Runbook

Short operator reference for the `bayanat update` flow.

::: warning Requires v5.0.0 or later
Releases before v5.0.0 do not ship an `update` command. Getting an older install
onto v5 is a one-time manual step, documented in
[Upgrading](/deployment/upgrading#upgrading-to-v5).
:::

## Triggering an update

Updates are applied from the shell, as root:

```
sudo bayanat update [<tag>]     # defaults to the latest release
```

Root is required to stop and start services, write to `/opt/bayanat`, and take
snapshots. To see what an update would move you to without changing anything:

```
bayanat update --check
```

The update runs in the foreground and prints each phase as it goes. It is not
backgrounded, so run it inside `tmux` or `screen` on a connection you do not
trust to stay up. Service logs during the window:

```
sudo journalctl -u bayanat -u bayanat-celery -f
```

## What the admin interface shows

The interface is read-only for updates. It never applies one.

- A background check runs every 6 hours and caches the latest published
  release.
- Administrators get a notification when a newer release appears, and a chip in
  the navigation bar linking to its release notes.
- The snapshots page lists pre-update snapshots. Restoring stays on the CLI,
  deliberately: a restore drops and recreates tables and should not be one
  click away in a browser.

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

## Release verification

The updater downloads each release as a signed tarball and verifies it against
a pinned minisign key before installing. An unsigned or
tampered release is refused during PREPARE with `Release <tag> is unsigned` or
`Signature verification FAILED`, and nothing is installed. If you hit this on a
legitimate release, the release is missing its `.minisig` asset; see
[release-signing.md](release-signing.md).

## If something goes wrong

### Migration failed (Alembic transaction rolled back)

Nothing to do. Services restart on the previous release automatically.
The UI shows the `error` field. Report the broken release; the previous
version keeps running.

### Health check failed after swap (rollback succeeded)

Nothing to do. The updater reverted the symlink and restarted on the
previous release. The pre-update snapshot is retained at
`/opt/bayanat/shared/backups/`.

One exception: if the previous release predates v5.0.0, the updater reverts the
symlink but leaves the services stopped and reports NEEDS_INTERVENTION. That is
deliberate. The database has already been migrated, and an older release running
against a newer schema is worse than being down. Restore the snapshot it names
to finish the recovery.

### NEEDS_INTERVENTION

Reached when the new release was broken and reverting the code did not, on its
own, produce a healthy install: either the previous release also failed its
health check, or it predates v5.0.0 and cannot serve the migrated schema.
Services are left stopped, so the web server returns 502 rather than exposing a
half-working application. Recover:

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
| `/opt/bayanat/state/update.json` | Current update state (sanitized JSON) |
| `/opt/bayanat/state/update.lock` | PID lock file |
| `/opt/bayanat/shared/backups/` | Pre-update snapshots |
| `/health` (Flask endpoint) | 200 = DB + Redis reachable |

## Manual CLI reference

Commands marked `(root)` require `sudo bayanat ...`; the others can run
as the app user via `sudo -u bayanat bayanat ...`.

```
bayanat update [<tag>]       (root)  default: latest GitHub release
bayanat update --check               show current vs latest; no changes
bayanat update --recover     (root)  recover a stuck state file
bayanat harden               (root)  migrate an older install onto the hardened layout
bayanat snapshots            (root)  list pre-update snapshots
bayanat restore <name>       (root)  interactive restore from a snapshot
bayanat status                       version + services + update state
```

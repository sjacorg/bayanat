# Changelog

## v5.1.5

### Added

- Web import settings show when the cookies were last updated and list each cookie domain with its number of cookies and earliest expiry, highlighting cookies that have expired or expire within 14 days. Cookie values are never shown.

### Fixed

- Adding a potential or claimed violation category no longer fails with "No response from server" behind a reverse proxy that does not forward the original host.
- Media import with "Optimize" enabled now uploads the converted copy to S3 storage; previously only the original reached the bucket and the copy's record pointed at a missing file.
- Files from web import are named by their actual type: direct image links are stored as images instead of `.mp4` files. Downloads without uploader information no longer create empty sources.
- Loading or saving an actor, bulletin or incident no longer reads its full revision history to get the last modified date, which made records with long histories slow.
- The installer no longer fails when Caddy's package repository is unavailable: it falls back to the package from Caddy's latest GitHub release, checked against the published checksums. Caddy installed this way does not receive updates through apt.
- The installer refuses Ubuntu releases older than 24.04 up front, instead of failing partway through on Ubuntu 22.04.

### Security

- When a release has no signature, the updater no longer suggests installing it by hand.
- oauthlib upgraded to 4.0.0 (CVE-2026-49264, CVE-2026-49265) and werkzeug to 3.1.9 (CVE-2026-102598).

### Documentation

- Auto-update runbook: what to do when `bayanat update` cannot complete; there is no manual upgrade procedure.
- Web import: routing all downloads, including those handed to ffmpeg, through Tor with Privoxy, and an nftables rule set that keeps the Celery worker on that route.
- Configuration: guidance for multi-gigabyte evidence files.

### Upgrading

No database migrations. Installer-managed installs update with `sudo bayanat update`. Ubuntu 24.04 or newer is now required for installs and updates: upgrade an Ubuntu 22.04 host before updating.

## v5.1.4

### Fixed

- Storage settings accept access keys and secrets in the formats used by S3-compatible providers (for example OVHcloud), not only AWS-shaped keys.
- Screenshot uploads pass the configured region to S3, so providers that require a region no longer fail there.
- `flask db upgrade` completes on a database with no migration stamp that already has the v5 schema, instead of failing with "already exists".

### Security

- pypdf upgraded to 6.19.0 (excessive CPU and memory use on crafted PDFs, GHSA-5jq2-8x83-x246 and related advisories) and urllib3 to 2.8.0 (GHSA-gh4c-6fx4-qh6g, GHSA-vxq7-64xx-v4gw, GHSA-8988-9cw3-xx77).

### Upgrading

No new database migrations. Installer-managed installs update with `sudo bayanat update`.

## v5.1.3

### Added

- S3-compatible storage providers (OVH, Cloudflare R2, MinIO, Wasabi, Backblaze and others) are supported: set `AWS_ENDPOINT_URL` in `.env`. Region names in the provider's own format are accepted, and with the Content Security Policy enabled, media served from the custom endpoint is allowed.
- `bayanat status` reports whether the installed systemd units match the current release, and `bayanat update` warns when a release changes them.

### Fixed

- Web import of YouTube now uses the JavaScript runtime and challenge solver that yt-dlp requires (shipped with the release), so downloads that worked from the yt-dlp command line no longer fail or lose formats in Bayanat.
- Web import keeps cookies in memory instead of leaving them in temporary files, saving settings no longer fails when cookies are configured, HLS downloads honour the configured proxy, and a failed import tells the user why.
- Saving user settings no longer erases other saved settings, and an unsupported language falls back to the default instead of breaking pages.
- In the Arabic interface, the add location dialog opens on the correct side.
- Docker: finishing the setup wizard and saving settings reload the application and restart the Celery workers, no manual container restart needed.
- The Event Types "Save" button is translated, and several dialog buttons use consistent styles.

### Changed

- Web imports and audio or video media imports fail with a clear message when ffmpeg or ffprobe is missing, instead of storing degraded files. The installer installs both; `flask doctor` reports when they are missing.

### Upgrading

No database migrations. Installer-managed installs update with `sudo bayanat update`. On hardened installs, then run `sudo bayanat harden --force` once to apply the updated Celery service unit; `bayanat status` shows "Units: out of date" until you do. Manual installs: older versions could leave web-import cookie files (`tmp*`) in the system temporary directory; they can be deleted.

## v5.1.2

### Fixed

- Users whose saved language setting was empty got an error on every page after signing in. They now get the default language.
- In the English interface, the related bulletins, actors and incidents search in the bulletin editor opened over the wrong side of the screen. It now opens as a side panel on the right (on the left in Arabic), and the actor and incident editors use the same side panel instead of a centred dialog.

### Security

- Vendored axios upgraded to 1.20.0 (GHSA-9fr6-4gfg-395g, GHSA-x97p-jq2g-jp4f and related advisories).

### Upgrading

No database migrations. Installer-managed installs update with `sudo bayanat update`. Installs on v5.0.0 or v5.1.0 run the old updater for this hop; if it stops at "MIGRATE: stopping services", re-run `sudo bayanat update`.

## v5.1.1

### Fixed

- `bayanat update` could abort at "MIGRATE: stopping services" with `Job for bayanat-celery.service canceled.`, leaving the web service stopped until the command was re-run. The updater no longer touches the worker-restart sentinel on every run, and the stop is retried and rolled back if the services will not stop.

### Changed

- `bayanat update` now hands over to the CLI shipped inside the verified release right after the signature check, so updater fixes apply to the update that installs them. Installs on v5.0.0 or v5.1.0 run the old updater once more for this hop; if that hop stops with the error above, re-run `sudo bayanat update`.

### Security

- WeasyPrint upgraded to 70.0 (GHSA-jf6q-chmf-3h3v, SSRF). The PDF export resource guard is ported to WeasyPrint's new fetcher API with the same allow rules, and now also refuses redirects, so an allowed host cannot bounce a fetch to another origin.
- DOMPurify in the documentation site upgraded to 3.4.13 (GHSA-55q2-fjhq-7xh7, XSS).

### Upgrading

No database migrations. Installer-managed installs on v5.0.0 or v5.1.0 update with `sudo bayanat update`; re-run it once if the first attempt stops at "MIGRATE: stopping services".

## v5.1.0

### Added

- Label structure navigator: a searchable, read-only tree of the label hierarchy, opened from the app bar by Admin, Mod and DA users. It shows each label's English and Arabic path, which entity types it applies to, and marks grouping-only and retired labels. Labels and verified labels are browsed as separate trees. Managing labels remains restricted to Admin and Mod.
- System users list search: Admins, and Mods with permission to view usernames, can search users by name, username or email. For Mods without that permission, the search returns no results, so it cannot be used to discover identities they cannot see.

### Changed

- Interface consistency pass across the Bulletins, Actors, Incidents, Sources, Labels, Locations and Event Types pages: the active quick filter is highlighted, the Advanced Search and Location Search dialogs keep their header visible while scrolling, Self-Assign dialogs gain a Cancel button, edit icons and Import CSV buttons are uniform, and table columns on the settings pages are rebalanced, with long text truncated and shown in full on hover. The Import from Web button is now visually secondary to New Bulletin.

### Upgrading

No database migrations. Installer-managed installs on v5.0.0 update with `sudo bayanat update`.

## v5.0.0

v5 changes how Bayanat is deployed as well as what it runs. Read
[Upgrading](https://github.com/sjacorg/bayanat/blob/main/docs/deployment/upgrading.md)
before starting: depending on your deployment this is a migration with a
maintenance window, not a routine pull.

### Breaking Changes

- **The web application and the worker run as separate accounts** (`bayanat-web`
  and `bayanat-celery`), both `nologin` members of the `bayanat` group. The
  `bayanat` user remains as the deployment and database identity.
- **The release tree is read-only to the services.** Anything previously written
  inside a release directory now writes into `shared/`, and `config.json` moves
  to `shared/runtime/config.json`, located by `BAYANAT_CONFIG_FILE`.
- **PostgreSQL local authentication uses peer authentication with an ident map.**
  The previous permissive rule for the application role is removed.
- **Redis requires a password.** `requirepass` is set in `redis.conf` and
  `REDIS_PASSWORD` in `.env`.
- **The uWSGI socket moves to `/run/bayanat/bayanat.sock`.** Installs predating
  this keep working through a fallback to the in-release socket.
- **Docker: PostgreSQL moves from 15 to 16**, which requires dumping and
  restoring the database volume. The Redis data volume path also changes.
- **Raw OCR provider payloads are no longer stored** and the text-map overlay is
  removed. Existing rows keep their payloads until cleared with
  `flask ocr purge-raw`.

### Deployment and Updates

- **`bayanat update`**: updates an installer-managed install to a chosen release.
  It verifies the release signature, takes a database snapshot, runs migrations
  with the services stopped, swaps the release and health-checks it, reverting
  automatically if that check fails. Supported from v5.0.0 onward; no earlier
  release ships an `update` command, so moving an existing install onto v5 is a
  documented one-time step.
- **`bayanat harden`**: migrates an install provisioned before v5 onto the
  least-privilege layout. Deliberately separate from `update`, because it
  rewrites both authentication backends, the service units and the web server
  configuration, and a code update must never leave those half-written. It backs
  up every file it touches with ownership and mode recorded, and restores all of
  it if the result fails its health check.
- **`bayanat snapshots`** and **`bayanat restore`** list and restore pre-update
  database snapshots.
- **`bayanat status`** reports the running version, service state, layout and
  update state.
- **Releases are verified before installation.** Each release ships a signed
  tarball, checked against a pinned minisign key; an unsigned or tampered
  release is refused.
- **Updates are applied from the command line only.** The interface reports that
  a newer release exists and links its notes, but never triggers an update or a
  restore. A web-reachable update would turn an authenticated admin session into
  root-level code execution on the host.
- **Production-ready Docker deployment** with a Caddy edge doing automatic
  HTTPS, health-gated startup ordering, digest-pinned images and non-root
  containers.

### Security

- Findings from an independent third-party security audit were remediated and
  retested, covering access control, session handling, input validation, file
  handling and deployment posture.
- Login endpoint throttling per account and per source address, configurable via
  `LOGIN_RATE_LIMIT_PER_USERNAME` and `LOGIN_RATE_LIMIT_PER_IP`.
- Configurable idle session timeout via `SESSION_LIFETIME`.
- The initial administrator is provisioned by the installer instead of an
  unauthenticated setup endpoint.
- Public archive export no longer leaks the internal description field (#346).

### Search

- Background search: a search that exceeds `SEARCH_TIMEOUT` is handed to a
  worker and the user is notified when results are ready, instead of failing
  (#372).
- Saved searches dropdown in the main search bar (#392).
- Fixed advanced search refine and extend combination logic (#361).
- Fixed a stale typeahead debounce race (#387).
- Lookup typeahead endpoints search translated titles (#365).
- `%` and `_` typed into search are treated as literal characters rather than
  SQL wildcards (#403).

### Import and Export

- Media over 5 GiB now reach S3 via multipart upload (#384).
- Imports terminate correctly when a media upload fails (#385), no longer stick
  in Pending on stale database connections (#327), and keep the import signal
  alive across chunked uploads (#334).
- Exports include every media file per item rather than only the first (#362).
- Public archive export with a `public_description` field (#345).
- A file whose type cannot be identified fails the import cleanly instead of
  crashing the worker and leaving a bulletin with no media attached (#408).

### Documents and Media

- Document and image redaction, burning redactions into a derived copy and
  leaving the original untouched (#349), honouring EXIF orientation (#357).

### Interface

- Right-to-left layout support (#380).
- Translated titles for location admin levels, location types and lookup tables
  (#369, #370).
- Label hierarchy paths shown in label previews (#379).
- Contextual user guide links across mapped pages and dialogs (#303).
- The running version is shown in the profile dropdown and dashboard footer
  (#388).
- Sessions stay alive during active typing and reading, with a warning before
  expiry (#395), and notification polling no longer slides the idle timeout
  (#343).
- Clearer dynamic form builder with feedback on field creation (#391).
- Reorganised system configuration screens (#298).
- Independent incident scope for event types (#355).
- Actor relations are mirrored and type-converted on create and update (#359).
- Secondary-language actor names shown in lists when the primary is empty (#363).
- Role save and CSV import report failures instead of failing silently. The
  session-replay queue is removed: after reauthenticating, the original form is
  still open and the action can simply be repeated (#407).

### Fixed

- Search: incident violation filters, the Unassigned toggle for actors and
  incidents, location tag search, geospatial reset, and Search Terms and
  Exclude Terms now normalize Arabic letter variants on both sides, backed by
  new indexes. Event location filters can include sub-locations, and the
  geospatial circle applies to the same event in single-event mode.
- Media dashboard: search by media, bulletin or actor ID, date range on the
  date shown, actor media shows its parent, and "cannot read" is reversible.
- Forms: sources autocompletes keep the typed search after a pick, events need
  only a type, an actor created from a bulletin inherits its ID as origin ID,
  and the date picker closes the previous calendar.
- Data integrity: a source with sub-sources or in use can no longer be deleted;
  label restrictions apply when a parent match expands to its children.
- Non-admin users no longer see a permission error on every page from the
  update-check banner.
- Password resets performed outside the web flow now clear the force-reset flag,
  which previously left the account stuck in a redirect loop (#337).
- Orphan actors are no longer left behind by interrupted create requests (#371).
- Stale Celery messages expire, and notifications guard against missing users
  (#389).
- Multiple Alembic heads are detected rather than failing part-way through a
  deployment (#374).

### Dependencies

- Python dependencies upgraded and Dependabot enabled (#402); GitHub Actions
  updated (#404); vendored front-end libraries refreshed (#353); TinyMCE
  upgraded (#347); `flask-security-too` pinned below 5.8 for
  [GHSA-f66q-9rf6-8795](https://github.com/advisories/GHSA-f66q-9rf6-8795)
  (#360).
- PyMuPDF is imported under its `pymupdf` name rather than the deprecated
  `fitz` alias (#405).

## v4.0.2

### Security

- Bumped vulnerable dependencies in `uv.lock`:
  - `urllib3` 2.6.3 → 2.7.0 (high, [GHSA-48p4-8xcf-vxj5](https://github.com/advisories/GHSA-48p4-8xcf-vxj5) sensitive headers forwarded across origins in proxied redirects; [GHSA-pq67-6m6q-mj2v](https://github.com/advisories/GHSA-pq67-6m6q-mj2v) decompression-bomb bypass in streaming API)
  - `lxml` 6.0.2 → 6.1.0 ([GHSA-pp7h-53gx-mx7r](https://github.com/advisories/GHSA-pp7h-53gx-mx7r), high, XXE in `iterparse`/`ETCompatXMLParser`)
  - `pillow` 12.1.1 → 12.2.0 ([GHSA-2vfv-wwj6-7q47](https://github.com/advisories/GHSA-2vfv-wwj6-7q47), high, FITS GZIP decompression bomb)
  - `pypdf` 6.10.0 → 6.10.2 (medium, three RAM-exhaustion advisories)
  - `python-dotenv` 1.2.1 → 1.2.2 (medium, symlink-following in `set_key`)
  - `Mako` 1.3.10 → 1.3.11 (medium, path traversal in `TemplateLookup`)
  - `pytest` 9.0.2 → 9.0.3 (dev, medium, vulnerable `tmpdir` handling)
- Bumped `axios` 1.15.0 → 1.16.0 (frontend dep, [GHSA-4hjh-wcwx-04pq](https://github.com/advisories/GHSA-4hjh-wcwx-04pq) DoS via large response).

### Fixed

- Admin "Reload" button now actually reloads the app. `uwsgi.ini` was missing the `touch-reload=reload.ini` directive, so the maintenance task touched the file with no effect on the running workers. After upgrading, existing installs should also append `touch-reload=reload.ini` to `/bayanat/uwsgi.ini` if they have local edits to that file.
- Allowed-extensions validator now accepts up to 5-character file extensions (previously capped at 4 characters). The cap rejected valid extensions like `mhtml`, `xhtml`, and `jhtml` from `MEDIA_ALLOWED_EXTENSIONS` and `SHEETS_ALLOWED_EXTENSIONS`.
- Restored the native browser PDF viewer for inline preview.

## v4.0.1

### Fixed

- Bulk OCR: celery worker now consumes the `ocr` queue. The systemd unit written by the installer was only subscribing to the default `celery` queue, so tasks dispatched by bulk OCR (UI and `flask ocr process`) silently piled up in Redis. Single-media OCR was not affected. Existing installs can fix in place by adding `-Q celery,ocr` to `ExecStart` in `/etc/systemd/system/bayanat-celery.service`, then `systemctl daemon-reload && systemctl restart bayanat-celery`.

## v4.0.0

### Database Migrations (Alembic)

Bayanat now uses Alembic (Flask-Migrate) for all schema changes. This replaces the old manual SQL migration files. Upgrading from v3 is a single command: `flask db upgrade`.

### OCR and Text Extraction

- New provider-agnostic OCR pipeline supporting Google Vision and any OpenAI-compatible LLM endpoint, replacing the prior inline Tesseract helper used during PDF import
- New `Extraction` table stores OCR results as first-class data with edit history
- Administrators switch OCR providers from the system administration dashboard (no restart required)
- Added PDF and DOCX text extraction (multi-page PDFs with configurable page cap)
- Parallelized bulk OCR processing with per-task isolation
- Text Map overlay: opt-in UI that draws per-word bounding boxes on document images (Google Vision only; falls back to plain text for LLM providers)
- Added search over extracted text (trigram-indexed) and on-demand translation
- S3 storage backend support throughout the OCR pipeline

### Notifications

- Notification drawer usability tweaks: hover-only mark-as-read icon, new mark-all-as-read button, subtler urgent-notification styling, wider drawer (#248)

### Search and UI

- Chips-based advanced text search
- Redesigned advanced search layout
- Actor map query visualization using Leaflet
- Redesigned labels management with hierarchy constraints
- Coordinates input for GeoMap without requiring map clicks
- PDF thumbnail rendering on media cards
- TinyMCE dark mode sync with Vuetify theme
- Color picker discoverability improvements
- Account security page redesign
- Personal vs organization settings clarification
- Activity monitor: renamed "Subject" to "Affected Item"
- Missing person profile: renamed "Last Address" to "Place of Disappearance"
- Username display in user dropdowns
- Fixed media preview and playback issues

### Security

- Content Security Policy (CSP) headers
- Exception message sanitization
- `can_access_media` permission for media dashboard
- Security headers on all responses
- views.py split into 18 sub-modules for better code isolation
- Added SECURITY.md and threat model documentation
- Dependency security patches: cryptography, pypdf, cbor2, pygments, yt-dlp, axios

### Performance

- Fixed N+1 query patterns in search and list views
- Pre-fetch OCR IDs instead of OR-subquery for search
- Media loading optimizations
- GIN trigram indexes on origin IDs and text extraction fields
- Increased uWSGI buffer-size to prevent 502 errors
- Font-display swap for faster text rendering

### Deployment and Tooling

- One-command installer with symlink-based releases (see [installation docs](docs/deployment/installation.md))
- `flask doctor` command for installation diagnostics
- Improved `flask check-db-alignment` with Alembic status and structured output
- Docker entrypoint now runs Alembic migrations automatically
- Ruff pre-commit hook for catching unused imports and syntax errors
- Lightweight pytest CI with service containers
- VitePress documentation site (replaces Wiki.js)

### Data Model

- New `Extraction` table for OCR results with edit history
- Dynamic fields: bug fixes and core field seeding for search dialogs
- Media orientation field for image rotation support
- Label constraints: self-parent prevention, sibling title uniqueness
- Media orphan cleanup and per-entity etag uniqueness

### Breaking Changes

- All deployments must run `flask db upgrade` (see upgrade guide)
- Old SQL migration files in `enferno/migrations/` are deprecated
- views.py split into sub-modules (import paths changed for `enferno.admin.views`)

### Upgrade Path

See [Upgrading to v4](docs/deployment/upgrading.md) for detailed instructions.

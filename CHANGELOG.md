# Changelog

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

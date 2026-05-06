# Changelog

## v4.0.2

### Security

- Bumped vulnerable dependencies in `uv.lock`:
  - `lxml` 6.0.2 → 6.1.0 ([GHSA-pp7h-53gx-mx7r](https://github.com/advisories/GHSA-pp7h-53gx-mx7r), high — XXE in `iterparse`/`ETCompatXMLParser`)
  - `pillow` 12.1.1 → 12.2.0 ([GHSA-2vfv-wwj6-7q47](https://github.com/advisories/GHSA-2vfv-wwj6-7q47), high — FITS GZIP decompression bomb)
  - `pypdf` 6.10.0 → 6.10.2 (medium — three RAM-exhaustion advisories)
  - `python-dotenv` 1.2.1 → 1.2.2 (medium — symlink-following in `set_key`)
  - `Mako` 1.3.10 → 1.3.11 (medium — path traversal in `TemplateLookup`)
  - `pytest` 9.0.2 → 9.0.3 (dev, medium — vulnerable `tmpdir` handling)

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

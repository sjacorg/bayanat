# Changelog

## v4.0.0

### Database Migrations (Alembic)

Bayanat now uses Alembic (Flask-Migrate) for all schema changes. This replaces the old manual SQL migration files. Upgrading from v3 is a single command: `flask db upgrade`.

### OCR and Text Extraction

- Unified OCR into provider-agnostic LLM support, replacing the Google Vision-only pipeline
- Added PDF and DOCX text extraction (non-OCR)
- Parallelized bulk OCR processing
- Added text map visualization for OCR results
- Added search and translation for extracted text
- S3 storage backend support for OCR

### Notifications

- Redesigned notification system with dedicated database table
- Email notification support with delivery tracking
- Read status, urgency flags, and categorization (Update, Alert, etc.)

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

- ID number types: actor `id_number` converted from string to JSONB array with type tracking
- Dynamic fields: bug fixes and core field seeding for search dialogs
- Notification table with email tracking
- Extraction table for OCR results with history
- Media orientation field for image rotation support
- Label constraints: self-parent prevention, sibling title uniqueness

### Breaking Changes

- All deployments must run `flask db upgrade` (see upgrade guide)
- Old SQL migration files in `enferno/migrations/` are deprecated
- views.py split into sub-modules (import paths changed for `enferno.admin.views`)

### Upgrade Path

See [Upgrading to v4](docs/deployment/upgrading.md) for detailed instructions.

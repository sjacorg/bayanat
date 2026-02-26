<p align="center">
  <a href="https://bayanat.org" target="_blank">
    <img alt="Bayanat" width="250" src="enferno/static/img/bayanat-h-v2.svg">
  </a>
</p>

[![Semgrep](https://github.com/sjacorg/bayanat/actions/workflows/semgrep.yml/badge.svg)](https://github.com/sjacorg/bayanat/actions/workflows/semgrep.yml)
[![pip-audit](https://github.com/sjacorg/bayanat/actions/workflows/pip-audit.yml/badge.svg)](https://github.com/sjacorg/bayanat/actions/workflows/pip-audit.yml)
[![Tests](https://github.com/sjacorg/bayanat/actions/workflows/run-tests.yml/badge.svg)](https://github.com/sjacorg/bayanat/actions/workflows/run-tests.yml)

Bayanat is an open source data management platform for processing human rights violations and war crimes data, developed and maintained by the [Syria Justice and Accountability Centre](https://syriaaccountability.org/) (SJAC). Watch this [video](https://www.youtube.com/watch?v=thCkihoXAk0) for a quick introduction.

## Features

- **Evidence management**: Track bulletins, actors, and incidents with rich metadata and entity relationships
- **Geospatial analysis**: PostGIS-powered queries with interactive Leaflet maps
- **Workflow management**: Built-in analysis and peer review workflow with role-based permissions
- **Advanced search**: Complex queries across all data fields with saved searches
- **Data import/export**: CSV, Excel, and media import tools with PDF/JSON/CSV export
- **Security**: WebAuthn/FIDO hardware keys, 2FA, CSRF protection, audit logging
- **Revision history**: Full snapshot-based change tracking with diff view
- **Access control**: Group-based item restriction for sensitive data

## Tech Stack

Flask, PostgreSQL/PostGIS, Vue.js 3, Vuetify, Celery, Redis

## Quick Start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/sjacorg/bayanat.git
cd bayanat
uv sync
bash gen-env.sh
uv run flask install
uv run flask run
```

See the full [installation guide](https://docs.bayanat.org/deployment/installation) for production deployment.

## Documentation

Full documentation is available at [docs.bayanat.org](https://docs.bayanat.org/).

## Live Demo

Try Bayanat at [demo.bayanat.org](https://demo.bayanat.org/).

## Localization

Help translate Bayanat on [POEditor](https://poeditor.com/join/project/XRamVw2AD0).

## Updates

Stable releases are pushed every few weeks. Critical updates are pushed sooner. Always **backup before pulling updates**. Check [releases](https://github.com/sjacorg/bayanat/releases) for migration instructions when needed.

## Support

Report bugs via [Issues](https://github.com/sjacorg/bayanat/issues).

## Contributing

See [Contributing Guidelines](./CONTRIBUTING.md) and [Code of Conduct](./CODE_OF_CONDUCT.md).

## License

GNU Affero General Public License v3.0. Distributed WITHOUT ANY WARRANTY.

Contributing to Bayanat
=======================

We appreciate all contributions to Bayanat no matter how small! Here are the current guidelines.

# New features

Unfortunately at this time, we're unable to accept contributions that adds a new feature to Bayanat. This is due to our current limited capacity. Adding a new code to Bayanat will require us to review the code thoroughly, especially to ensure the Bayanat's security isn't affected.

To that end we decided to reject any new change until further notice. We're working on expanding our capacity and we're hoping we can allow contributions that contain new features in the near future.

# Bug fixes

If you spotted a bug in Bayanat and would like to submit a fix, please first report the bug on GitHub. You can indicate in your report that you're going to submit a fix. We will need to be able to verify and reproduce the bug before accepting any fix.

# Submitting a contribution

You will need to open a new PR. We require an individual PR for each bug fix or new feature. PRs that combine multiple issues will be rejected. 

We'll add more guidelines very soon regarding formatting and documentation.

## Code Formatting Guidelines

### Overview

We use two main tools:

1. **Black** for Python files
2. **Prettier** for JavaScript and CSS files

We'll soon set guidelines for formatting our HTML files.

These tools are integrated into our development workflow via pre-commit hooks.

### Prerequisites

The required libraries and hooks are defined in `dev-requirements.txt` and `package.json`.


### Installation

1. Install Pre-commit and black:

   ```bash
   pip install -r dev-requirements.txt
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

3. Install the Pre-commit Hooks:

   Navigate to the root directory of bayanat and run:
   ```bash
   pre-commit install
   ```

### Usage

The pre-commit hooks will automatically format your staged files when you run `git commit`. However, you can also run the formatters manually.

1. Black (Python):

   To format a specific file or directory:
   ```bash
   black path/to/file_or_directory
   ```

2. Prettier (JS/CSS):

   To format a specific file:
   ```bash
   prettier --write path/to/file.js
   ```

### Configuration

The configuration for each tool is as follows:

- **Black:** Configured via `pyproject.toml`.
- **Prettier:** Configured via `.prettierrc`.

# Database Migrations

All database migrations should be placed in `enferno/migrations/` using the following conventions:

### Naming Convention

Migration files should be prefixed with a timestamp in `YYYYMMDD_HHMMSS` format, followed by a descriptive name:

```
enferno/migrations/
├── 20250113_153045_add_users_table.sql
├── 20250114_090012_add_index_to_x.sql
└── 20250114_120501_update_email_constraint.sql
```

### Creating Migration Files

You can generate the timestamp prefix using either:

Python:
```python
from datetime import datetime
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
```

Bash:
```bash
date +"%Y%m%d_%H%M%S"
```

This naming convention ensures:
- Clear chronological ordering of migrations
- Prevents filename collisions when multiple developers create migrations
- Makes it easy to track when changes were introduced

# Tests

Bayanat comes with e2e tests using pytest and pydantic models. To run the tests, install the dependencies with
```bash
pip install -r dev-requirements.txt
```

Bayanat tests require a separate test database to be setup before running any tests.

After setting up the production database, follow the instructions below for creating a test database

```bash
sudo -u bayanat createdb bayanat_test
sudo -u postgres psql -d bayanat_test -c 'CREATE EXTENSION if not exists pg_trgm; CREATE EXTENSION if not exists postgis;'
```

After creating the test db, you can run the existing tests with
```bash
pytest
```

Tests define `pydantic` models to ensure the backend responses and frontend requests conform to expected database schema.

# Auto-Docs

Bayanat backend code is documented in ReStructured Text format (loosely following Google's guidelines).

To generate automatic documentation in html format, you can follow the following steps:

1. Make sure `sphinx` is installed on your system
2. Navigate to bayanat directory on terminal
3. Run `sphinx-apidoc -f -o docs/source enferno && sphinx-apidoc -f -o docs/source tests`
4. Run `sphinx-build -M html docs/source/ docs/build/`, you will see multiple warning messages on your terminal. Ignore them.

Following these steps, the html files generated will be available under `docs/build/html`
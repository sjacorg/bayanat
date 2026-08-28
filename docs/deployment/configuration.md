# Configuration

Most settings can be configured from the frontend. A few must be set in the `.env` file.

For interactive setup:

```bash
bash gen-env.sh
```

Or manually copy `.env-sample` to `.env` and edit.

## Secure Cookies

Bayanat uses secure cookies by default (requires HTTPS). For development:

```
SECURE_COOKIES=False
```

::: danger
Do not disable secure cookies in production.
:::

## Secret Key

`SECRET_KEY` keeps sessions secure. Generate a strong key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

::: warning
Changing the secret key logs out all users.
:::

## PostgreSQL

Required for Docker deployment. Optional for native installs on the same host.

- `POSTGRES_DB`: Database name (default: `bayanat`)
- `POSTGRES_HOST`: Host (empty for local, `postgres` for Docker)
- `POSTGRES_PASSWORD`: Password (not required for local)
- `POSTGRES_USER`: Username (not required for local)

## Redis

Required for Docker deployment.

- `REDIS_HOST`: Host (empty for local, `redis` for Docker)
- `REDIS_PASSWORD`: Password, if set

## Password Salt

`SECURITY_PASSWORD_SALT` must be generated and kept secret:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

::: danger
Changing the password salt invalidates all user passwords.
:::

## Two-Factor Authentication

Generate a TOTP secret for `SECURITY_TOTP_SECRETS`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

See [Flask Security docs](https://flask-security-too.readthedocs.io/en/stable/two_factor_configurations.html).

::: danger
Changing this secret invalidates all 2FA configurations.
:::

## Storage

### Local

Media files stored in `enferno/media/` relative to the application directory. An
installer-managed v5 host keeps them in `/opt/bayanat/shared/media`, which the
release symlinks into place, so the application path is the same either way.

### Amazon S3

Configure the S3 bucket with correct policies, block public access, and set up CORS.

## Search

Interactive searches run under a database statement timeout. When a search exceeds it, the query is cancelled and re-run by a background worker instead of failing, and the user is notified when the results are ready. See [Search](/guide/search) for what this looks like in the interface.

| Variable | Default | Purpose |
|---|---|---|
| `SEARCH_TIMEOUT` | `30` | Seconds an interactive search may run before it is handed to the background. `0` disables the behaviour and searches run unbounded. |
| `BACKGROUND_SEARCH_TIME_LIMIT` | `600` | Seconds the background re-run may take before it is abandoned. |

Background searches require a running Celery worker. Without one, users receive the "continuing in the background" message but never get results.

::: warning
Lowering `SEARCH_TIMEOUT` far below the default sends ordinary searches to the background, including the initial page load of a list view. Raise it instead if legitimate searches are being deferred.
:::

## Sessions and Login Throttling

| Variable | Default | Purpose |
|---|---|---|
| `SESSION_LIFETIME` | `3600` | Seconds of inactivity before a session expires and the user must sign in again. |
| `LOGIN_RATE_LIMIT_PER_USERNAME` | `10 per 15 minutes` | Failed-login throttle applied per account, so one targeted account cannot be brute-forced from many addresses. |
| `LOGIN_RATE_LIMIT_PER_IP` | `30 per 15 minutes` | Failed-login throttle applied per source address, so one address cannot spray many accounts. |

Both throttles use the `limits` string syntax, for example `5 per minute` or
`100 per hour`. They apply to the login endpoint only. Lowering
`SESSION_LIFETIME` too far is a common cause of complaints about constant
re-authentication.

## Configuration File Location

| Variable | Default | Purpose |
|---|---|---|
| `BAYANAT_CONFIG_FILE` | `config.json` | Path to the feature-toggle configuration file. |

Installer-managed deployments set this to a path outside the release directory,
because releases are read-only to the services and `config.json` is written at
runtime from the admin interface. Set it explicitly if you deploy releases as
read-only trees.

## Data Import

Enable path scanning with `ETL_ALLOWED_PATH`.

::: warning
Only enable path scanning when needed.
:::

## Backups

See [Backups](/deployment/backups) for configuration.

## Offline Maps

For offline or privacy-focused deployments, run your own tile server using [openstreetmap-tile-server](https://github.com/Overv/openstreetmap-tile-server). Update the Maps API Endpoint in system settings.

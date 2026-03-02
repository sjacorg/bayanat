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

Media files stored in `enferno/media/`.

### Amazon S3

Configure the S3 bucket with correct policies, block public access, and set up CORS.

## Data Import

Enable path scanning with `ETL_ALLOWED_PATH`.

::: warning
Only enable path scanning when needed.
:::

## Backups

See [Backups](/deployment/backups) for configuration.

## Offline Maps

For offline or privacy-focused deployments, run your own tile server using [openstreetmap-tile-server](https://github.com/Overv/openstreetmap-tile-server). Update the Maps API Endpoint in system settings.

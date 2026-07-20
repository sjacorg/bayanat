# Docker Deployment

::: warning Beta
Docker Compose deployment is still in beta. For production environments, [native installation](/deployment/installation) is recommended.
:::

## Prerequisites

- Docker Engine with the Compose v2 plugin (`docker compose`, not the legacy `docker-compose` binary)
- `.env.docker` file configured (see [Configuration](/deployment/configuration))

## Quick Start

```bash
docker compose --env-file .env.docker up -d
```

This starts PostgreSQL, Redis, the Flask app, NGINX, and Celery.

::: tip
The `--env-file .env.docker` flag is required so Compose can substitute `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}`, and `${REDIS_PASSWORD}` placeholders in `docker-compose.yml`. Without it, those services boot with empty credentials and the Flask container fails to connect.
:::

## First Admin User

The entrypoint creates an `admin` user automatically on the first startup
(when the database has no schema yet) and prints a one-time random
password to the container logs. Retrieve it with:

```bash
docker compose --env-file .env.docker logs bayanat | grep -A4 "Generated password"
```

Sign in at the Bayanat URL with `admin` and the printed password. The
setup wizard runs after first login. Change the admin password from your
account settings afterwards.

If the auto-bootstrap was missed or the admin account was deleted, run
the CLI directly:

```bash
docker compose --env-file .env.docker exec bayanat uv run flask install -u admin
```

It generates a fresh password and prints it. If an admin already exists
the command exits without changing anything.

## Development

```bash
docker compose -f docker-compose-dev.yml up
```

## Testing

```bash
docker compose -f docker-compose-test.yml up
```

# Docker Deployment

::: warning Beta
Docker Compose deployment is still in beta. For production environments, [native installation](/deployment/installation) is recommended.
:::

## Prerequisites

- Docker and Docker Compose installed
- `.env` file configured (see [Configuration](/deployment/configuration))

## Quick Start

```bash
docker-compose up -d
```

This starts PostgreSQL, Redis, the Flask app, NGINX, and Celery.

## First Admin User

The entrypoint creates an `admin` user automatically on the first startup
(when the database has no schema yet) and prints a one-time random
password to the container logs. Retrieve it with:

```bash
docker-compose logs bayanat | grep -A4 "Generated password"
```

Sign in at the Bayanat URL with `admin` and the printed password, then
change it from your account settings.

If the auto-bootstrap was missed or the admin account was deleted, run
the CLI directly:

```bash
docker-compose exec bayanat uv run flask install -u admin
```

It generates a fresh password and prints it. If an admin already exists
the command exits without changing anything.

## Development

```bash
docker-compose -f docker-compose-dev.yml up
```

## Testing

```bash
docker-compose -f docker-compose-test.yml up
```

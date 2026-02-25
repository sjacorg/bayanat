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

## Create Admin User

```bash
docker-compose exec bayanat uv run flask install
```

## Development

```bash
docker-compose -f docker-compose-dev.yml up
```

## Testing

```bash
docker-compose -f docker-compose-test.yml up
```

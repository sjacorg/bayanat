# Installation

Bayanat can be deployed natively on a Linux system or using Docker.

::: warning
Although this guide follows best security practices, you still need to secure the server itself (firewall, VPN, HTTPS, etc.).
:::

## Quick Install

The fastest way to get Bayanat running on a fresh Ubuntu server. One command installs all dependencies, sets up the database, configures HTTPS, and starts the services.

**Requirements:** Ubuntu 22.04+ with root access and a domain pointing to the server's IP.

**With a domain (recommended, automatic HTTPS):**

```bash
curl -sL https://raw.githubusercontent.com/sjacorg/bayanat/main/bayanat | sudo bash -s install yourdomain.com
```

**Without a domain (HTTP only, for testing):**

```bash
curl -sL https://raw.githubusercontent.com/sjacorg/bayanat/main/bayanat | sudo bash -s install
```

This will:
- Install system packages (PostgreSQL, Redis, Caddy, ffmpeg, etc.)
- Create the `bayanat` system user
- Set up the database
- Clone the latest release into `/opt/bayanat/releases/`
- Install Python dependencies via `uv`
- Configure Caddy as a reverse proxy with automatic SSL
- Set up systemd services for Bayanat and Celery
- Start everything

Once complete, open your domain in a browser. The setup wizard will guide you through creating an admin account and configuring the application.

**Check status:**

```bash
sudo bayanat status
```

::: tip
The quick installer uses a symlink-based release structure at `/opt/bayanat/` with shared configuration and media that persists across updates. See the [architecture documentation](/deployment/architecture) for details.
:::

## Manual Installation

The following steps are for Ubuntu. They should work on other Linux distributions with equivalent packages.

::: tip
You can install Bayanat by following these steps exactly without changes. Adjust only if you have specific requirements (e.g., PostgreSQL on another host).
:::

### Install System Packages

**Ubuntu 22.04:**

```bash
sudo apt install build-essential python3-dev python3.10-venv libjpeg8-dev libzip-dev libxml2-dev libssl-dev libffi-dev libxslt1-dev libmysqlclient-dev libncurses5-dev python-setuptools postgresql postgresql-contrib python3-pip libpq-dev git redis-server libimage-exiftool-perl postgis ffmpeg libpango-1.0-0 libpangoft2-1.0-0 libglib2.0-0
```

**Ubuntu 24.04:**

```bash
sudo apt install build-essential python3.12 python3.12-dev python3.12-venv python3-pip libjpeg8-dev libzip-dev libxml2-dev libssl-dev libffi-dev libxslt1-dev libmysqlclient-dev libncurses5-dev postgresql postgresql-contrib python3-pip libpq-dev git libimage-exiftool-perl postgis ffmpeg redis-server libpango-1.0-0 libpangoft2-1.0-0 libglib2.0-0
```

**macOS (local development):**

```bash
brew install postgresql redis pango glib libffi exiftool ffmpeg
```

Optionally install Tesseract OCR:

```bash
sudo apt install -y tesseract-ocr
```

Install language packages as needed (e.g., `tesseract-ocr-eng`). See [Tesseract installation docs](https://tesseract-ocr.github.io/tessdoc/Installation.html).

Install the latest [NGINX](https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-open-source/#installing-a-prebuilt-ubuntu-package-from-the-official-nginx-repository).

### Create System User

```bash
sudo adduser --disabled-password bayanat
```

### Setup Database

```bash
sudo -u postgres createuser bayanat
sudo -u postgres createdb -O bayanat bayanat
sudo -u postgres psql -d bayanat -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d bayanat -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### Install Bayanat

```bash
sudo mkdir /bayanat && sudo chown bayanat:bayanat /bayanat
sudo -u bayanat -i
cd /bayanat
git clone https://github.com/sjacorg/bayanat .
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if not already available.

```bash
uv sync
```

For voice transcription (Whisper) and OCR (Tesseract):

```bash
uv sync --extra ai
```

### Configure

Generate the `.env` file interactively:

```bash
bash gen-env.sh
```

See [Configuration](/deployment/configuration) for manual setup.

### Initialize Database

Create the database tables, roles, and default data. The create-exts flag creates extensions in the bayanat db for postgis and pg_trgm

```bash
uv run flask create-db --create-exts
```

### Create Admin User

```bash
uv run flask install
```

### Test

```bash
uv run flask run
```

Access at [http://127.0.0.1:5000](http://127.0.0.1:5000). The setup wizard will guide further configuration.

::: warning
`flask run` is development mode only. Continue with the steps below for production.
:::

Exit the `bayanat` user (`Ctrl-D` or `exit`) to continue with a privileged user.

## Run as a Service

Create `/etc/systemd/system/bayanat.service`:

```ini
[Unit]
Description=Bayanat uWSGI Service
After=network.target postgresql.service redis-server.service

[Service]
User=bayanat
Group=bayanat
WorkingDirectory=/bayanat
ExecStart=/bayanat/.venv/bin/uwsgi --ini uwsgi.ini
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bayanat
```

## NGINX Configuration

Create `/etc/nginx/conf.d/bayanat.conf`:

```nginx
server {
    listen 80;
    server_name example.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Replace `example.com` with your domain. Use [Certbot](https://certbot.eff.org/) for HTTPS.

```bash
sudo systemctl restart nginx
```

## Running Celery

Create `/etc/systemd/system/bayanat-celery.service`:

```ini
[Unit]
Description=Bayanat Celery Service
After=network.target redis-server.service

[Service]
User=bayanat
Group=bayanat
WorkingDirectory=/bayanat
ExecStart=/bayanat/.venv/bin/celery -A enferno.tasks worker -B --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bayanat-celery
```

## Docker

::: warning Beta
Docker deployment is still in beta. For production, native deployment is recommended.
:::

After [configuring](/deployment/configuration) and generating a `.env` file:

```bash
docker-compose up -d
```

Install the admin user:

```bash
docker-compose exec bayanat uv run flask install
```

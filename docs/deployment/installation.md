# Installation

Bayanat can be deployed natively on a Linux system or using Docker.

::: warning
Although this guide follows best security practices, you still need to secure the server itself (firewall, VPN, HTTPS, etc.).
:::

## Manual Installation

The following steps are for Ubuntu. They should work on other Linux distributions with equivalent packages.

::: tip
You can install Bayanat by following these steps exactly without changes. Adjust only if you have specific requirements (e.g., PostgreSQL on another host).
:::

### Install System Packages

**Ubuntu 22.04:**

```bash
sudo apt install -y python3-dev libpq-dev redis-server postgresql postgresql-contrib postgis libgdal-dev uwsgi
```

**Ubuntu 24.04:**

```bash
sudo apt install -y python3-dev libpq-dev redis-server postgresql postgresql-contrib postgis libgdal-dev uwsgi
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

#!/bin/bash
set -e

log() { echo "[$(date '+%H:%M:%S')] $1"; }
error() { echo "[ERROR] $1" >&2; exit 1; }

# Get domain and repository
DOMAIN="${DOMAIN:-${1:-localhost}}"
REPO="${REPO:-sjacorg/bayanat}"
GIT_URL="https://github.com/${REPO}.git"
log "Installing Bayanat for: $DOMAIN"
log "Repository: $REPO"

[ "$EUID" -eq 0 ] || error "Must run as root"

# Install packages
log "Installing packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    git postgresql postgresql-contrib postgis redis-server \
    python3 python3-pip python3-venv python3-dev build-essential \
    libpq-dev libxml2-dev libxslt1-dev libssl-dev libffi-dev \
    libjpeg-dev libzip-dev libimage-exiftool-perl ffmpeg curl wget jq

# Install uv globally
log "Installing uv..."
set -o pipefail
curl -LsSf https://astral.sh/uv/install.sh | sh
set +o pipefail
cp ~/.local/bin/uv /usr/local/bin/ 2>/dev/null || cp ~/.cargo/bin/uv /usr/local/bin/
chmod 755 /usr/local/bin/uv

# Install Caddy
log "Installing Caddy..."
rm -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -fsSL 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -fsSL 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -qq && apt-get install -y -qq caddy

# Setup users and database
systemctl enable --now postgresql redis-server
id bayanat &>/dev/null || useradd -m bayanat
id bayanat-daemon &>/dev/null || useradd --system -m bayanat-daemon

log "Setting up database..."
sudo -u postgres createuser -s bayanat 2>/dev/null || true
sudo -u postgres createdb bayanat -O bayanat 2>/dev/null || true

# Configure PostgreSQL trust auth
PG_CONFIG="/etc/postgresql/*/main/pg_hba.conf"
grep -q "local.*bayanat.*trust" $PG_CONFIG 2>/dev/null || {
    sed -i '/^local.*all.*postgres.*peer/a local   all             bayanat                                 trust' $PG_CONFIG
    systemctl reload postgresql
}

# Setup application
log "Setting up application..."
[ -f /opt/bayanat/run.py ] || {
    rm -rf /opt/bayanat

    # Clone with full history to avoid detached HEAD and enable updates
    log "Cloning repository..."
    git clone "$GIT_URL" /opt/bayanat

    # Get latest release tag from remote (source of truth) and checkout
    log "Checking for latest release tag..."
    LATEST_TAG=$(git ls-remote --tags --refs --sort=-version:refname "$GIT_URL" | head -n1 | sed 's/.*refs\/tags\///')

    if [ -n "$LATEST_TAG" ]; then
        log "Checking out release: $LATEST_TAG"
        git -C /opt/bayanat checkout "$LATEST_TAG"
    else
        log "No release tags found, staying on main branch"
    fi
}
chown -R bayanat:bayanat /opt/bayanat

sudo -u bayanat REPO="$REPO" bash << 'SETUP'
cd /opt/bayanat && export PATH=/usr/local/bin:$PATH

uv sync --frozen

[ -f .env ] || {
    chmod +x gen-env.sh
    ./gen-env.sh -n -o
}

export FLASK_APP=run.py
uv run flask create-db --create-exts
uv run flask import-data
SETUP

# Create configs
cat > /opt/bayanat/uwsgi.ini << 'EOF'
[uwsgi]
module = run:app
processes = 4
http = 127.0.0.1:5000
die-on-term = true
EOF

cat > /etc/systemd/system/bayanat.service << 'EOF'
[Unit]
Description=UWSGI instance to serve Bayanat
After=network.target

[Service]
User=bayanat
Group=bayanat
WorkingDirectory=/opt/bayanat
EnvironmentFile=/opt/bayanat/.env
ExecStart=/opt/bayanat/.venv/bin/uwsgi --ini uwsgi.ini
Restart=always
RestartSec=1
StartLimitIntervalSec=0
Type=notify
KillMode=mixed
KillSignal=SIGQUIT
TimeoutStopSec=5
TimeoutStartSec=30
StandardOutput=journal
StandardError=journal
NotifyAccess=all

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/bayanat-celery.service << 'EOF'
[Unit]
Description=Bayanat Celery Service
After=network.target

[Service]
User=bayanat
Group=bayanat
WorkingDirectory=/opt/bayanat
EnvironmentFile=/opt/bayanat/.env
ExecStart=/opt/bayanat/.venv/bin/celery -A enferno.tasks worker --autoscale 2,5 -B
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Configure web server
if [ "$DOMAIN" = "localhost" ]; then
    # For localhost/IP-only access
    cat > /etc/caddy/Caddyfile << 'EOF'
:80 {
    reverse_proxy 127.0.0.1:5000

    handle_path /static/* {
        root * /opt/bayanat/enferno/static
        file_server
    }

    request_body {
        max_size 100MB
    }
}
EOF
else
    # For domain-based access with automatic HTTPS
    # Note: Only configure the domain, Caddy will handle HTTP->HTTPS redirect automatically
    cat > /etc/caddy/Caddyfile << EOF
$DOMAIN {
    reverse_proxy 127.0.0.1:5000

    handle_path /static/* {
        root * /opt/bayanat/enferno/static
        file_server
    }

    request_body {
        max_size 100MB
    }
}
EOF
fi

mkdir -p /var/log/caddy && chown caddy:caddy /var/log/caddy

# Setup daemon permissions for service restarts only
cat > /etc/sudoers.d/bayanat-daemon << 'EOF'
bayanat-daemon ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active bayanat
bayanat-daemon ALL=(ALL) NOPASSWD: /usr/bin/systemd-run --on-active=1s /usr/bin/systemctl restart bayanat
bayanat-daemon ALL=(ALL) NOPASSWD: /usr/bin/systemd-run --on-active=1s /usr/bin/systemctl restart caddy
bayanat-daemon ALL=(ALL) NOPASSWD: /usr/bin/systemd-run --on-active=1s /usr/bin/systemctl restart bayanat-celery
EOF

# Create API handler
cat > /usr/local/bin/bayanat-handler.sh << 'HANDLER'
#!/bin/bash
LOG_FILE="/var/log/bayanat/api.log"
log() { echo "$(date -Iseconds) $*" >> "$LOG_FILE"; }

read -r method path protocol
while IFS= read -r line && [ "$line" != $'\r' ]; do
    [[ "$line" =~ ^Content-Length:[[:space:]]*([0-9]+) ]] && content_length="${BASH_REMATCH[1]}"
done

body=""
[ -n "$content_length" ] && [ "$content_length" -gt 0 ] && read -r -N "$content_length" body

respond() { printf "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n%s" ${#1} "$1"; }

case "$path" in
    "/restart-service")
        log "Restart request - body='$body'"
        service=$(echo "$body" | jq -r '.service // empty')
        log "Extracted service: '$service'"
        [[ "$service" =~ ^(bayanat|caddy|bayanat-celery)$ ]] && {
            log "Restarting $service"
            respond "{\"success\":true,\"message\":\"$service restarting\"}"
            sudo /usr/bin/systemd-run --on-active=1s /usr/bin/systemctl restart "$service"
        } || {
            log "Invalid service: '$service'"
            respond '{"success":false,"error":"Invalid service"}'
        }
        ;;
    "/health")
        sudo /usr/bin/systemctl is-active bayanat >/dev/null 2>&1 &&
            respond '{"success":true,"status":"healthy"}' ||
            respond '{"success":false,"status":"unhealthy"}'
        ;;
    *) respond '{"error":"Not found"}' ;;
esac
HANDLER

chmod +x /usr/local/bin/bayanat-handler.sh
mkdir -p /var/log/bayanat && chown -R bayanat-daemon:bayanat-daemon /var/log/bayanat

# Create socket services (CRITICAL API FEATURE)
cat > /etc/systemd/system/bayanat-api.socket << 'EOF'
[Unit]
Description=Bayanat API Socket
[Socket]
ListenStream=127.0.0.1:8080
Accept=yes
[Install]
WantedBy=sockets.target
EOF

cat > /etc/systemd/system/bayanat-api@.service << 'EOF'
[Unit]
Description=Bayanat API Handler
[Service]
Type=oneshot
User=bayanat-daemon
Group=bayanat-daemon
ExecStart=/usr/local/bin/bayanat-handler.sh
StandardInput=socket
StandardOutput=socket
EOF

# Start services
systemctl daemon-reload
systemctl enable --now bayanat bayanat-celery bayanat-api.socket
systemctl enable --now caddy

# Restart Caddy to reload the custom configuration
systemctl restart caddy

# Status
echo ""
echo "✅ Bayanat Installation Complete!"
if [ "$DOMAIN" = "localhost" ]; then
    echo "🌐 Access: http://$(hostname -I | awk '{print $1}')"
else
    echo "🌐 Access: https://$DOMAIN"
    echo "   Note: Caddy will automatically redirect HTTP to HTTPS"
    echo "   First access may take a few seconds while obtaining SSL certificate"
fi
echo "🔧 API: curl localhost:8080/health"
echo "📊 Services: $(systemctl is-active bayanat bayanat-celery caddy bayanat-api.socket | tr '\n' ' ')"

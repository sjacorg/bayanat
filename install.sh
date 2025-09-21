#!/bin/bash
set -e

log() { echo "[$(date '+%H:%M:%S')] $1"; }
error() { echo "[ERROR] $1" >&2; exit 1; }

# Get domain and repository
DOMAIN="${DOMAIN:-${1:-$(curl -s https://ipinfo.io/ip 2>/dev/null || echo 127.0.0.1)}}"
REPO="${REPO:-https://github.com/sjacorg/bayanat.git}"
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
    libjpeg-dev libzip-dev libimage-exiftool-perl ffmpeg curl wget

# Install uv globally
log "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
cp ~/.cargo/bin/uv /usr/local/bin/ 2>/dev/null || cp ~/.local/bin/uv /usr/local/bin/
chmod 755 /usr/local/bin/uv

# Install Caddy
log "Installing Caddy..."
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -qq && apt-get install -y -qq caddy

# Setup users and database
systemctl enable --now postgresql redis-server
id bayanat &>/dev/null || useradd -m bayanat
id bayanat-daemon &>/dev/null || useradd --system -m bayanat-daemon

log "Setting up database..."
sudo -u postgres createuser -s bayanat 2>/dev/null || true
sudo -u postgres createdb bayanat -O bayanat 2>/dev/null || true

# Configure PostgreSQL trust auth
PG_CONFIG=$(find /etc/postgresql -name pg_hba.conf | head -1)
grep -q "local.*bayanat.*trust" "$PG_CONFIG" 2>/dev/null || {
    sed -i '/^local.*all.*postgres.*peer/a local   all             bayanat                                 trust' "$PG_CONFIG"
    systemctl reload postgresql
}

# Setup application
log "Setting up application..."
[ -f /opt/bayanat/run.py ] || {
    rm -rf /opt/bayanat
    git clone "$REPO" /opt/bayanat
}
chown -R bayanat:bayanat /opt/bayanat

sudo -u bayanat bash << 'SETUP'
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
[[ "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && SITE_ADDR="http://$DOMAIN" || SITE_ADDR="$DOMAIN"

cat > /etc/caddy/Caddyfile << EOF
$SITE_ADDR {
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

mkdir -p /var/log/caddy && chown caddy:caddy /var/log/caddy

# Setup daemon permissions (CRITICAL SECURITY FEATURE)
cat > /etc/sudoers.d/bayanat-daemon << 'EOF'
bayanat-daemon ALL=(ALL) NOPASSWD: /bin/systemctl restart bayanat, /bin/systemctl restart caddy, /bin/systemctl is-active bayanat, /bin/systemctl is-active caddy
bayanat-daemon ALL=(bayanat) NOPASSWD: /usr/bin/git -C /opt/bayanat pull
EOF

# Create API handler
cat > /usr/local/bin/bayanat-handler.sh << 'HANDLER'
#!/bin/bash
LOG_FILE="/var/log/bayanat/api.log"
log() { echo "$(date -Iseconds) $*" >> "$LOG_FILE"; }

read -r method path protocol
while IFS= read -r line && [ "$line" != $'\r' ]; do
    [[ "$line" =~ ^Content-Length:\ ([0-9]+) ]] && content_length="${BASH_REMATCH[1]}"
done

body=""
[ -n "$content_length" ] && [ "$content_length" -gt 0 ] && read -r -N "$content_length" body

respond() { printf "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n%s" ${#1} "$1"; }

case "$path" in
    "/update-bayanat")
        log "Starting update" && cd /opt/bayanat
        git_output=$(sudo -u bayanat git pull 2>&1)
        echo "$git_output" | grep -q "Already up to date" && { respond '{"success":true,"message":"Already up to date"}'; exit; }
        sudo -u bayanat bash -c "cd /opt/bayanat && PATH=/usr/local/bin:\$PATH uv sync --frozen"
        sudo -u bayanat bash -c "cd /opt/bayanat && PATH=/usr/local/bin:\$PATH FLASK_APP=run.py uv run flask apply-migrations"
        sudo systemctl restart bayanat
        respond '{"success":true,"message":"Updated successfully"}'
        ;;
    "/restart-service")
        service=$(echo "$body" | sed -n 's/.*"service":"\([^"]*\)".*/\1/p')
        [[ "$service" =~ ^(bayanat|caddy)$ ]] && {
            sudo systemctl restart "$service"
            respond "{\"success\":true,\"message\":\"$service restarted\"}"
        } || respond '{"success":false,"error":"Invalid service"}'
        ;;
    "/health")
        sudo systemctl is-active bayanat >/dev/null 2>&1 &&
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

sudo -u bayanat-daemon git config --global --add safe.directory /opt/bayanat

# Start services
systemctl daemon-reload
systemctl enable --now bayanat bayanat-celery bayanat-api.socket
systemctl enable caddy
systemctl restart caddy  # Restart to trigger certificate acquisition
sleep 5

# Status
echo ""
echo "✅ Bayanat Installation Complete!"
echo "🌐 Access: ${DOMAIN/127.0.0.1/http://127.0.0.1}"
echo "🔧 API: curl localhost:8080/health"
systemctl is-active bayanat bayanat-celery caddy bayanat-api.socket | paste <(echo -e "Bayanat\nCelery\nCaddy\nAPI") - | column -t
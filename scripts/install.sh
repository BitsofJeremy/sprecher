#!/bin/bash
# Sprecher Install Script
# Idempotent install of systemd service + nginx config
# Mac/Linux compatible

set -e

SERVICE_NAME="sprecher-web"
PORT="${SPRECHER_PORT:-8400}"
WORK_DIR="${SPRECHER_WORK_DIR:-$HOME/sprecher}"
INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Sprecher Install ==="
echo "Service: $SERVICE_NAME"
echo "Port: $PORT"
echo "Work Dir: $WORK_DIR"
echo "Install Dir: $INSTALL_DIR"

# Detect platform
detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" == "ubuntu" ]] || [[ "$ID" == "debian" ]]; then
            echo "linux"
        else
            echo "linux"
        fi
    else
        echo "linux"
    fi
}

PLATFORM=$(detect_platform)
echo "Platform: $PLATFORM"

# Create work directory and data subdirs
mkdir -p "$WORK_DIR/data/uploads"
mkdir -p "$WORK_DIR/data/chunks"
mkdir -p "$WORK_DIR/data/output"
mkdir -p "$WORK_DIR/data/voices"

# Linux: systemd service
install_systemd() {
    echo "Installing systemd service..."

    SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Sprecher - Unified TTS/STT Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$INSTALL_DIR
Environment="SPRECHER_WORK_DIR=$WORK_DIR"
Environment="SPRECHER_PORT=$PORT"
ExecStart=$INSTALL_DIR/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    echo "Systemd service installed: $SERVICE_FILE"
}

# Linux: nginx config
install_nginx() {
    echo "Installing nginx config..."

    NGINX_SITE="/etc/nginx/sites-available/$SERVICE_NAME"
    NGINX_ENABLED="/etc/nginx/sites-enabled/$SERVICE_NAME"

    cat > "$NGINX_SITE" << EOF
server {
    listen 80;
    server_name _;

    # Increase body size for file uploads
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;

        # HTMX support
        proxy_set_header HX-Request \$http_hx_request;
        proxy_set_header HX-Trigger \$http_hx_trigger;
        proxy_set_header HX-Target \$http_hx_target;
    }

    location /audio/ {
        alias $WORK_DIR/data/;
        internal;
    }

    location /static/ {
        alias $INSTALL_DIR/static/;
    }
}
EOF

    # Enable site
    if [[ -L "$NGINX_ENABLED" ]]; then
        rm "$NGINX_ENABLED"
    fi
    ln -sf "$NGINX_SITE" "$NGINX_ENABLED"

    # Test and reload
    if command -v nginx &> /dev/null; then
        nginx -t && systemctl reload nginx
        echo "Nginx config installed: $NGINX_SITE"
    else
        echo "Nginx not found - skipping. Config at: $NGINX_SITE"
    fi
}

# macOS: launchd plist (optional)
install_launchd() {
    echo "Installing launchd plist..."

    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_FILE="$PLIST_DIR/com.sprecher.plist"

    mkdir -p "$PLIST_DIR"

    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sprecher</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/.venv/bin/python</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>$PORT</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>SPRECHER_WORK_DIR</key>
        <string>$WORK_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$WORK_DIR/sprecher.log</string>
    <key>StandardErrorPath</key>
    <string>$WORK_DIR/sprecher.err</string>
</dict>
</plist>
EOF

    launchctl load "$PLIST_FILE" 2>/dev/null || true
    echo "Launchd plist installed: $PLIST_FILE"
}

# Main install
if [[ "$PLATFORM" == "linux" ]]; then
    if [[ $EUID -eq 0 ]]; then
        install_systemd
        install_nginx
    else
        echo "Not running as root - skipping systemd/nginx install"
        echo "To install manually:"
        echo "  sudo ./scripts/install.sh"
    fi
elif [[ "$PLATFORM" == "macos" ]]; then
    install_launchd
fi

echo ""
echo "=== Install Complete ==="
echo ""
echo "To start the service:"
if [[ "$PLATFORM" == "linux" ]] && [[ $EUID -eq 0 ]]; then
    echo "  sudo systemctl start $SERVICE_NAME"
elif [[ "$PLATFORM" == "macos" ]]; then
    echo "  launchctl load ~/Library/LaunchAgents/com.sprecher.plist"
else
    echo "  cd $INSTALL_DIR && uv run uvicorn app.main:app --port $PORT"
fi
echo ""
echo "Web UI: http://localhost:$PORT"
echo "API: http://localhost:$PORT/api"

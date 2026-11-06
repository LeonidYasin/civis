#!/bin/bash
set -e

SERVICE_FILE="/etc/systemd/system/civis.service"
CIVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing Civis systemd service from $CIVIS_DIR..."

cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Civis Telegram Bot (Marketplace OS Gateway)
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$CIVIS_DIR/civis_bot
ExecStart=$(which python3) bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
EnvironmentFile=-$CIVIS_DIR/civis_bot/.env

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "Enabling and starting civis service..."
sudo systemctl enable --now civis

echo "✅ Civis service installed and started!"
sudo systemctl status civis --no-pager

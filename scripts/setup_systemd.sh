#!/usr/bin/env bash
# ==============================================================================
# Wilo AI Water Transfer System — Systemd Service Installer for Raspberry Pi
# ==============================================================================
# Automatically detects current user, python3 path, npm path, and repository path.
# Configures and enables:
#   1. wilo-pump.service     (Pump controller & hardware safety loop)
#   2. wilo-server.service   (Flask telemetry & API backend on port 5050)
#   3. wilo-frontend.service (React Vite frontend preview on port 8080)
# ==============================================================================

set -e

if [ "$EUID" -eq 0 ]; then
    echo "⚠️ Please run this script as your regular user (e.g. wilopi), NOT as root or with sudo directly."
    echo "   The script will use sudo when writing service files."
    exit 1
fi

CURRENT_USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="$(which python3 || echo /usr/bin/python3)"
NPM_BIN="$(which npm || echo /usr/bin/npm)"

echo "=========================================================="
echo "  Installing Wilo AI Water Transfer System Services"
echo "  User:             ${CURRENT_USER}"
echo "  Repository Root:  ${REPO_DIR}"
echo "  Python:           ${PYTHON_BIN}"
echo "  NPM:              ${NPM_BIN}"
echo "=========================================================="

# 1. Build frontend if needed
if [ ! -d "${REPO_DIR}/dashboard/dist" ]; then
    echo "📦 Building dashboard frontend for production..."
    cd "${REPO_DIR}/dashboard"
    ${NPM_BIN} install
    ${NPM_BIN} run build
    cd "${REPO_DIR}"
fi

# 2. Configure wilo-pump.service
cat <<EOF | sudo tee /etc/systemd/system/wilo-pump.service > /dev/null
[Unit]
Description=Wilo Water Pump Controller & Hardware Safety Engine
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${REPO_DIR}
ExecStart=${PYTHON_BIN} src/controller/pump_controller.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Safety: ensure GPIO pins released and pump forced OFF on crash/stop
ExecStopPost=${PYTHON_BIN} -c "import RPi.GPIO as G; G.setmode(G.BCM); G.setup(17,G.OUT); G.output(17,G.HIGH); G.cleanup()"

[Install]
WantedBy=multi-user.target
EOF

# 3. Configure wilo-server.service
cat <<EOF | sudo tee /etc/systemd/system/wilo-server.service > /dev/null
[Unit]
Description=Wilo Water Pump Flask API Backend
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${REPO_DIR}
ExecStart=${PYTHON_BIN} src/dashboard/server.py --port 5050
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 4. Configure wilo-frontend.service
cat <<EOF | sudo tee /etc/systemd/system/wilo-frontend.service > /dev/null
[Unit]
Description=Wilo Water Pump React Production Frontend (Port 8080)
After=network.target wilo-server.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${REPO_DIR}/dashboard
ExecStart=${NPM_BIN} run preview -- --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable services
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "✅ Enabling services for automatic start on boot..."
sudo systemctl enable wilo-server.service
sudo systemctl enable wilo-frontend.service
sudo systemctl enable wilo-pump.service

echo "🚀 Starting services..."
sudo systemctl restart wilo-server.service
sudo systemctl restart wilo-frontend.service
sudo systemctl restart wilo-pump.service

echo ""
echo "=========================================================="
echo "🎉 Wilo System Services Installed & Started!"
echo "   Dashboard:  http://$(hostname -I | awk '{print $1}'):8080"
echo "   Backend:    http://127.0.0.1:5050"
echo "=========================================================="
echo "Check status anytime with:"
echo "   sudo systemctl status wilo-server wilo-frontend wilo-pump"

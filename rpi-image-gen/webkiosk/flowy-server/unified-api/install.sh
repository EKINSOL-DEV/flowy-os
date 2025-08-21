#!/bin/bash

# Flowy Unified API Installation Script
# This script sets up the unified API system with systemd service

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/flowy/unified-api"
SERVICE_NAME="flowy-unified-api"
LOG_DIR="/flowy/logs"
CONFIG_DIR="/etc/flowy"

echo "=== Flowy Unified API Installation ==="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "This script should not be run as root. Please run as a regular user with sudo access."
    exit 1
fi

# Create flowy user if it doesn't exist
if ! id "flowy" &>/dev/null; then
    echo "Creating flowy user..."
    sudo useradd -r -s /bin/false -d /opt/flowy -c "Flowy System User" flowy
fi

# Create directories
echo "Creating directories..."
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$LOG_DIR"
sudo mkdir -p "$CONFIG_DIR"

# Copy files
echo "Installing files..."
sudo cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/config.yaml" "$CONFIG_DIR/unified-api.yaml"

# Set permissions
echo "Setting permissions..."
sudo chown -R flowy:flowy "$INSTALL_DIR"
sudo chown -R flowy:flowy "$LOG_DIR" 
sudo chmod -R 755 "$INSTALL_DIR"
sudo chmod -R 755 "$LOG_DIR"
sudo chmod 644 "$CONFIG_DIR/unified-api.yaml"

# Make main script executable
sudo chmod +x "$INSTALL_DIR/flowy_unified_api.py"

# Install systemd service
echo "Installing systemd service..."
sudo cp "$INSTALL_DIR/flowy-unified-api.service" /etc/systemd/system/
sudo systemctl daemon-reload

# Enable service
echo "Enabling service..."
sudo systemctl enable "$SERVICE_NAME"

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    pip3 install -r "$INSTALL_DIR/requirements.txt" --user
else
    echo "Installing basic dependencies..."
    pip3 install fastapi uvicorn pyyaml psutil --user
fi

# Create log rotation configuration
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/flowy-unified-api > /dev/null <<EOF
$LOG_DIR/*/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 flowy flowy
    postrotate
        systemctl reload-or-restart flowy-unified-api
    endscript
}
EOF

# Test configuration
echo "Testing configuration..."
cd "$INSTALL_DIR"
if python3 -c "import config_loader; config_loader.get_config(); print('Configuration valid')"; then
    echo "✓ Configuration is valid"
else
    echo "✗ Configuration error - please check config.yaml"
    exit 1
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Configuration file: $CONFIG_DIR/unified-api.yaml"
echo "Log directory:      $LOG_DIR"
echo "Install directory:  $INSTALL_DIR"
echo ""
echo "API will be available at: http://localhost:8000/"
echo ""

# Ask if user wants to start the service now
read -p "Start the service now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting service..."
    sudo systemctl start "$SERVICE_NAME"
    sleep 3
    
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "✓ Service started successfully"
        echo "API should be available at: http://localhost:8000/"
    else
        echo "✗ Service failed to start. Check logs with:"
        echo "  sudo journalctl -u $SERVICE_NAME -n 20"
    fi
fi

echo ""
echo "Installation completed!"
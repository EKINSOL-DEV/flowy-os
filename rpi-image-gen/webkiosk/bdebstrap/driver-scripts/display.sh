#!/bin/bash
# setup_waveshare.sh - Adapted for bdebstrap chroot environment
# This script configures the Waveshare DSI panel for the image filesystem.
# It is based on the instructions provided in the Waveshare documentation:
# https://www.waveshare.com/wiki/10.1-DSI-TOUCH-A
#
# Usage: Called from customize02 with chroot directory as parameter
#   ./display.sh $1
#
# $1 = chroot directory path

set -e

# Use the chroot directory passed as parameter
CHROOT_DIR="$1"
CONFIG_FILE="$CHROOT_DIR/boot/firmware/config.txt"

echo "Configuring Waveshare display in image filesystem..."

# Create boot directories if they don't exist
mkdir -p "$CHROOT_DIR/boot/firmware"
mkdir -p "$CHROOT_DIR/boot/overlays"

# Install required packages for display support
chroot "$CHROOT_DIR" apt install -y \
    device-tree-compiler \
    build-essential \
    linux-headers-generic || true

# Check if config.txt exists, create if not
if [ ! -f "$CONFIG_FILE" ]; then
    touch "$CONFIG_FILE"
fi

# Check if Waveshare configuration already exists
if grep -q "Waveshare.*DSI.*TOUCH-A" "$CONFIG_FILE"; then
    echo "Waveshare display configuration already exists in config.txt."
else
    echo "Adding Waveshare display configuration to config.txt..."
    cat >> "$CONFIG_FILE" << 'EOF'

# Waveshare 10.1" DSI TOUCH-A configuration
dtoverlay=vc4-kms-v3d
# DSI1 Use
dtoverlay=vc4-kms-dsi-waveshare-panel-v2,10_1_inch_a
# DSI0 Use (uncomment if using DSI0 instead of DSI1)
# dtoverlay=vc4-kms-dsi-waveshare-panel-v2,10_1_inch_a,dsi0
EOF
    echo "Display overlay configuration added."
fi

echo "Waveshare display configured in image filesystem."
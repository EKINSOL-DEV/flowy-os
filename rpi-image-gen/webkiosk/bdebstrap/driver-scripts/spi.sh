#!/bin/bash
# spi.sh - Enable SPI interface for bdebstrap chroot environment
# This script enables SPI in the image filesystem for NFC readers and other SPI devices.
#
# Usage: Called from customize02 with chroot directory as parameter
#   ./spi.sh $1
#
# $1 = chroot directory path

set -e

# Use the chroot directory passed as parameter
CHROOT_DIR="$1"
CONFIG_FILE="$CHROOT_DIR/boot/firmware/config.txt"

echo "Configuring SPI interface in image filesystem..."

# Create boot directories if they don't exist
mkdir -p "$CHROOT_DIR/boot/firmware"

# Install required packages for SPI and driver compilation
echo "Installing SPI and driver build dependencies..."
chroot "$CHROOT_DIR" apt update
chroot "$CHROOT_DIR" apt install -y \
    device-tree-compiler \
    build-essential \
    spi-tools \
    i2c-tools \
    python3-spidev || true

# Check if config.txt exists, create if not
if [ ! -f "$CONFIG_FILE" ]; then
    touch "$CONFIG_FILE"
fi

# Enable SPI interface
if grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
    echo "SPI is already enabled in config.txt."
else
    echo "Enabling SPI interface in config.txt..."
    cat >> "$CONFIG_FILE" << 'EOF'

# Enable SPI interface
dtparam=spi=on

# Pi 5 specific SPI configuration - enable both SPI buses
dtoverlay=spi0-1cs
dtoverlay=spi1-1cs
EOF
    echo "SPI interface enabled with Pi 5 compatibility."
fi

echo "SPI interface configuration completed - ready for NFC and other SPI devices."

# Create SPI group if it doesn't exist and add user
echo "Setting up SPI permissions..."
chroot "$CHROOT_DIR" groupadd -f spi
chroot "$CHROOT_DIR" usermod -a -G spi "$IGconf_device_user1" || true

# Create udev rule for SPI device permissions
echo "Creating SPI device permissions..."
cat > "$CHROOT_DIR/etc/udev/rules.d/99-spi.rules" << 'EOF'
# Allow users in spi group to access SPI devices
SUBSYSTEM=="spidev", GROUP="spi", MODE="0664"
EOF

echo "SPI configuration completed."
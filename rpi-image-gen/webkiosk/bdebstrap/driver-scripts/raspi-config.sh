#!/bin/bash
# raspi-config.sh - Configure Raspberry Pi hardware interfaces using raspi-config
# This script enables SPI, I2C, and other hardware interfaces for peripherals.
#
# Usage: Called from customize02 with chroot directory as parameter
#   ./raspi-config.sh $1
#
# $1 = chroot directory path

set -e

CHROOT_DIR="$1"

echo "Configuring Raspberry Pi hardware interfaces using raspi-config..."

# Use raspi-config to enable hardware interfaces (non-interactive)
echo "Enabling SPI interface..."
chroot "$CHROOT_DIR" raspi-config nonint do_spi 0

# echo "Enabling I2C interface..."  
# chroot "$CHROOT_DIR" raspi-config nonint do_i2c 0

echo "Enabling SSH..."
chroot "$CHROOT_DIR" raspi-config nonint do_ssh 0

# Add user to hardware access groups
echo "Setting up hardware device permissions..."
chroot "$CHROOT_DIR" usermod -a -G spi,i2c,gpio,render "$IGconf_device_user1" || true

echo "Raspberry Pi hardware interface configuration completed."
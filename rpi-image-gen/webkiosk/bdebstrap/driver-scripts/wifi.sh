#!/bin/bash
# set -e

CHROOT_DIR="$1"
chroot "$CHROOT_DIR" apt install -y wpasupplicant network-manager firmware-brcm80211

# Configure WiFi template for NetworkManager
mkdir -p "$CHROOT_DIR/etc/NetworkManager/system-connections"
cp ../../templates/rpi/wifi-template.nmconnection "$CHROOT_DIR/etc/NetworkManager/system-connections/WiFi-Template.nmconnection"
chmod 600 "$CHROOT_DIR/etc/NetworkManager/system-connections/WiFi-Template.nmconnection"
chroot "$CHROOT_DIR" chown root:root /etc/NetworkManager/system-connections/WiFi-Template.nmconnection
#!/bin/bash
# set -e

CHROOT_DIR="$1"
chroot "$CHROOT_DIR" apt install -y wpasupplicant network-manager firmware-brcm80211
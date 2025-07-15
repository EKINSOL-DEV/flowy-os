#!/bin/bash
# setup_audio.sh - Adapted for bdebstrap chroot environment
#
# This script adds the Hifiberry DAC overlay to the Raspberry Pi's config.txt,
# ensuring that the Hifiberry DAC becomes the default audio device.
#
# Usage: Called from customize02 with chroot directory as parameter
#   ./audio.sh $1
#
# $1 = chroot directory path

set -e

# Use the chroot directory passed as parameter
CHROOT_DIR="$1"
CONFIG_FILE="$CHROOT_DIR/boot/firmware/config.txt"

echo "Configuring audio in image filesystem..."

# Create boot/firmware directory if it doesn't exist
mkdir -p "$CHROOT_DIR/boot/firmware"

# Check if config.txt exists, create if not
if [ ! -f "$CONFIG_FILE" ]; then
    touch "$CONFIG_FILE"
fi

# Check if the dtoverlay for hifiberry-dac is already present.
if grep -q "^dtoverlay=hifiberry-dac" "$CONFIG_FILE"; then
    echo "The dtoverlay=hifiberry-dac entry already exists in config.txt."
else
    echo "Adding dtoverlay=hifiberry-dac to config.txt..."
    # Append the overlay entry at the end of the file.
    echo "" >> "$CONFIG_FILE"
    echo "dtoverlay=hifiberry-dac" >> "$CONFIG_FILE"
    echo "Audio overlay entry added."
fi

echo "Hifiberry DAC configured in image filesystem."
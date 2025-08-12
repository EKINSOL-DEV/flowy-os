#!/bin/bash
# setup_audio.sh - Adapted for bdebstrap chroot environment
#
# This script adds the Hifiberry DAC overlay to the Raspberry Pi's config.txt,
# installs raspotify, and configures it for the image filesystem.
#
# Usage: Called from customize02 with chroot directory as parameter
#   ./audio.sh $1
#
# $1 = chroot directory path

# set -e

# Use the chroot directory passed as parameter
CHROOT_DIR="$1"
CONFIG_FILE="$CHROOT_DIR/boot/firmware/config.txt"
TEMPLATES_DIR="${RPI_TEMPLATES:-../../../templates/rpi}"

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

# Install curl and raspotify in chroot environment
echo "Installing curl and raspotify..."
chroot "$CHROOT_DIR" apt-get update
chroot "$CHROOT_DIR" apt-get install -y curl
chroot "$CHROOT_DIR" bash -c "curl -sL https://dtcooper.github.io/raspotify/install.sh | sh"

# Configure raspotify with template file
echo "Configuring raspotify..."
RASPOTIFY_CONF_TEMPLATE="$TEMPLATES_DIR/raspotify.conf"
TARGET_CONF="$CHROOT_DIR/etc/raspotify/conf"

# Create the raspotify config directory if it doesn't exist
mkdir -p "$CHROOT_DIR/etc/raspotify"

if [ ! -f "$RASPOTIFY_CONF_TEMPLATE" ]; then
    echo "Warning: Raspotify configuration template not found at $RASPOTIFY_CONF_TEMPLATE"
    echo "Skipping raspotify configuration."
else
    # Copy the template file and replace {hostname} with actual hostname placeholder
    # Note: The actual hostname replacement will happen at first boot
    cp "$RASPOTIFY_CONF_TEMPLATE" "$TARGET_CONF"
    echo "Raspotify configuration template installed."
    
    # Create a first-boot script to replace hostname placeholder
    mkdir -p "$CHROOT_DIR/etc/systemd/system"
    cat > "$CHROOT_DIR/etc/systemd/system/raspotify-hostname-setup.service" << 'EOF'
[Unit]
Description=Update raspotify hostname configuration
After=network.target
Before=raspotify.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'HOSTNAME=$(hostname); sed -i "s/{hostname}/$HOSTNAME/g" /etc/raspotify/conf'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    # Enable the hostname setup service
    chroot "$CHROOT_DIR" systemctl enable raspotify-hostname-setup.service
fi

echo "Audio configuration with raspotify completed."
#!/bin/sh
# Expand root partition and filesystem on first boot
set -e

ROOT_DEV=$(findmnt -no SOURCE /)
DISK_DEV=$(lsblk -ndo PKNAME "$ROOT_DEV")
PART_NUM=$(echo "$ROOT_DEV" | grep -o '[0-9]*$')

echo "Expanding partition $PART_NUM on /dev/$DISK_DEV..."
growpart "/dev/$DISK_DEV" "$PART_NUM"

echo "Resizing filesystem on $ROOT_DEV..."
resize2fs "$ROOT_DEV"

# Remove trigger file so this only runs once
rm -f /var/lib/flowy/.expand-rootfs

echo "Root filesystem expanded successfully."

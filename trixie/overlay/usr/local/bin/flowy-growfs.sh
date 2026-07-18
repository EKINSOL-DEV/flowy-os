#!/bin/bash
# One-shot: grow the root partition to fill the eMMC and resize the ext4.
# Runs at first boot (guarded by the done-flag via the systemd unit condition).
set -e
LOG=/var/log/flowy-growfs.log
{
echo "=== flowy-growfs $(date) ==="
/usr/sbin/parted ---pretend-input-tty /dev/mmcblk0 <<PEOF
resizepart 2 100%
Yes
quit
PEOF
/usr/sbin/resize2fs /dev/mmcblk0p2
df -h /
touch /var/lib/flowy-growfs.done
echo "=== done ==="
} >> "$LOG" 2>&1

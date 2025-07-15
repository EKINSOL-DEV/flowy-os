#!/bin/bash
# Simple, safer one-liner version

set -e  # Exit on any error

# Clean, build, and move with error handling
sudo rm -rf rpi-image-gen/work && \
mkdir -p images && \
[ -f images/latest.img ] && mv images/latest.img images/prev.img || true && \
(cd rpi-image-gen && ./build.sh -c generic64-apt-simple -D ./webkiosk -o ./webkiosk/image.options) && \
mv rpi-image-gen/work/*/deploy/*.img images/latest.img && \
echo "✅ Build completed! Image: images/latest.img"
#!/bin/bash
# Build script for flowy-os kiosk image

set -e  # Exit on any error

# Note: The underlying build system will handle privilege escalation as needed

# Use sudo to ask for password so the script won't randomy stop mid execution.
sudo echo ""

# Set absolute path to output directory for use by customize scripts.
export FLOWY_OUTPUT_DIR="$(pwd)/output"

# Parse arguments
BUILD_NFC=false
BUILD_THEMES=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --build-nfc)
      BUILD_NFC=true
      shift
      ;;
    --pack-themes)
      BUILD_THEMES=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--build-nfc] [--pack-themes] [--help]"
      echo "  --build-nfc   Rebuild NFC libraries archive from submodule"
      echo "  --pack-themes Pack Plymouth themes into archives"
      echo "  --help        Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Check if NFC archive exists, auto-trigger build if missing
if [ "$BUILD_NFC" = false ]; then
  if [ ! -f "$FLOWY_OUTPUT_DIR/libraries/libnfc.tar.xz" ]; then
    echo "📦 NFC archive not found, auto-triggering build..."
    BUILD_NFC=true
  fi
fi

# Build NFC libraries if requested or auto-triggered
if [ "$BUILD_NFC" = true ]; then
  ./build-nfc.sh
fi

# Pack themes if requested
if [ "$BUILD_THEMES" = true ]; then
  ./pack-themes.sh
fi

# Clean, build, and move with error handling
sudo rm -rf rpi-image-gen/work && \
mkdir -p "$FLOWY_OUTPUT_DIR/images" && \
[ -f "$FLOWY_OUTPUT_DIR/images/latest.img" ] && mv "$FLOWY_OUTPUT_DIR/images/latest.img" "$FLOWY_OUTPUT_DIR/images/prev.img" || true && \
(cd rpi-image-gen && ./build.sh -c webkiosk/config/flowy-kiosk.cfg -D ./webkiosk -o ./webkiosk/image.options) && \
mv rpi-image-gen/work/*/deploy/*.img "$FLOWY_OUTPUT_DIR/images/latest.img" && \
echo "✅ Build completed! Image: $FLOWY_OUTPUT_DIR/images/latest.img"
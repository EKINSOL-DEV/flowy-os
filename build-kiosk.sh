#!/bin/bash
# Build script for flowy-os kiosk image

set -e  # Exit on any error

# Start timing
START_TIME=$(date +%s)

# Note: The underlying build system will handle privilege escalation as needed

# Use sudo to ask for password so the script won't randomy stop mid execution.
sudo echo ""

# Set absolute path to output directory for use by customize scripts.
export FLOWY_OUTPUT_DIR="$(pwd)/output"

# Parse arguments
BUILD_NFC=false
BUILD_THEMES=false
BUILD_PROFILE="flowy-kiosk"  # default profile
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
    --minimal)
      BUILD_PROFILE="flowy-kiosk-minimal"
      shift
      ;;
    --full-hardware)
      BUILD_PROFILE="flowy-kiosk-full"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--build-nfc] [--pack-themes] [--minimal] [--full-hardware] [--help]"
      echo "  --build-nfc      Rebuild NFC libraries archive from submodule"
      echo "  --pack-themes    Pack Plymouth themes into archives"
      echo "  --minimal        Build ultra-minimal kiosk image (reduced base system)"
      echo "  --full-hardware  Build with full hardware development tools"
      echo "  --help           Show this help message"
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

# Create temporary options file with profile override
TEMP_OPTIONS="/tmp/build-options-$$.sh"
cp rpi-image-gen/webkiosk/image.options "$TEMP_OPTIONS"
if [ "$BUILD_PROFILE" != "flowy-kiosk" ]; then
  echo "device_profile=$BUILD_PROFILE" >> "$TEMP_OPTIONS"
fi

# Clean, build, and move with error handling
sudo rm -rf rpi-image-gen/work && \
mkdir -p "$FLOWY_OUTPUT_DIR/images" && \
[ -f "$FLOWY_OUTPUT_DIR/images/latest.img" ] && mv "$FLOWY_OUTPUT_DIR/images/latest.img" "$FLOWY_OUTPUT_DIR/images/prev.img" || true && \
echo "🔧 Building with profile: $BUILD_PROFILE" && \
(cd rpi-image-gen && ./build.sh -c flowy-kiosk.cfg -D ./webkiosk -o "$TEMP_OPTIONS") && \
if ls rpi-image-gen/work/*/deploy/*.img.zst 1> /dev/null 2>&1; then
    # Compressed image found
    cp rpi-image-gen/work/*/deploy/*.img.zst "$FLOWY_OUTPUT_DIR/images/latest.img.zst" && \
    echo "✅ Build completed! Compressed image: $FLOWY_OUTPUT_DIR/images/latest.img.zst" && \
    echo "📦 Size reduction: $(du -h rpi-image-gen/work/*/artefacts/*.img | cut -f1) → $(du -h $FLOWY_OUTPUT_DIR/images/latest.img.zst | cut -f1)" && \
    echo "💡 To use: zstd -d $FLOWY_OUTPUT_DIR/images/latest.img.zst"
else
    # Uncompressed image fallback
    mv rpi-image-gen/work/*/deploy/*.img "$FLOWY_OUTPUT_DIR/images/latest.img" && \
    echo "✅ Build completed! Image: $FLOWY_OUTPUT_DIR/images/latest.img"
fi

# Cleanup temporary options file
[ -f "$TEMP_OPTIONS" ] && rm -f "$TEMP_OPTIONS"

# Calculate and display total build time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))
SECONDS=$((DURATION % 60))

echo "⏱️  Total build time: ${HOURS}h ${MINUTES}m ${SECONDS}s"
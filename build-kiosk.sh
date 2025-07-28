#!/bin/bash
# Build script for flowy-os kiosk image

set -e  # Exit on any error

# Note: The underlying build system will handle privilege escalation as needed

# Set absolute path to output directory for use by customize scripts
export FLOWY_OUTPUT_DIR="$(pwd)/output"

# Parse arguments
BUILD_NFC=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --build-nfc)
      BUILD_NFC=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--build-nfc] [--help]"
      echo "  --build-nfc  Rebuild NFC libraries and Python module from submodule"
      echo "  --help       Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Check if NFC libraries exist, auto-trigger build if missing
if [ "$BUILD_NFC" = false ]; then
  if [ ! -f "$FLOWY_OUTPUT_DIR/libraries/libnfc_nci_linux.so" ] || [ ! -f "$FLOWY_OUTPUT_DIR/libraries/libpn7160_fw.so" ] || [ ! -f "$FLOWY_OUTPUT_DIR/libraries/nfc_native.cpython-311-aarch64-linux-gnu.so" ]; then
    echo "📦 NFC libraries not found, auto-triggering build..."
    BUILD_NFC=true
  fi
fi

# Build NFC libraries if requested or auto-triggered
if [ "$BUILD_NFC" = true ]; then
  echo "🔧 Building NFC libraries..."
  git submodule update --init --recursive
  cd dependencies/linux_libnfc-nci
  
  # Clean and build
  make clean || true
  ./bootstrap || true
  ./configure --enable-shared --disable-static
  make -j$(nproc)
  
  # Copy built libraries to output (without version numbers)
  mkdir -p "$FLOWY_OUTPUT_DIR/libraries" "$FLOWY_OUTPUT_DIR/python"
  cp .libs/libnfc_nci_linux-1.so.0.0.0 "$FLOWY_OUTPUT_DIR/libraries/libnfc_nci_linux.so"
  cp .libs/libpn7160_fw.so.0.0.0 "$FLOWY_OUTPUT_DIR/libraries/libpn7160_fw.so"
  
  # Build Python module
  echo "🐍 Building Python NFC module..."
  cd python
  ./build.sh
  
  # Copy Python module to output
  cp nfc_native*.so "$FLOWY_OUTPUT_DIR/libraries/"
  
  cd ../../..
  echo "✅ NFC libraries and Python module built and copied to output/"
fi

# Always copy nfc_reader Python module to ensure it's up to date
echo "📋 Copying nfc_reader Python module..."
git submodule update --init --recursive
mkdir -p "$FLOWY_OUTPUT_DIR/python"
cp dependencies/linux_libnfc-nci/python/nfc_reader.py "$FLOWY_OUTPUT_DIR/python/"

# Clean, build, and move with error handling
sudo rm -rf rpi-image-gen/work && \
mkdir -p "$FLOWY_OUTPUT_DIR/images" && \
[ -f "$FLOWY_OUTPUT_DIR/images/latest.img" ] && mv "$FLOWY_OUTPUT_DIR/images/latest.img" "$FLOWY_OUTPUT_DIR/images/prev.img" || true && \
(cd rpi-image-gen && ./build.sh -c generic64-apt-simple -D ./webkiosk -o ./webkiosk/image.options) && \
mv rpi-image-gen/work/*/deploy/*.img "$FLOWY_OUTPUT_DIR/images/latest.img" && \
echo "✅ Build completed! Image: $FLOWY_OUTPUT_DIR/images/latest.img"
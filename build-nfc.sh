#!/bin/bash
# NFC library builder script for flowy-os
# Builds libnfc-nci libraries and creates archive for installation

set -e  # Exit on any error

# Set absolute path to output directory
export FLOWY_OUTPUT_DIR="${FLOWY_OUTPUT_DIR:-$(pwd)/output}"

echo "🔧 Building NFC libraries..."

# Ensure submodule is up to date
git submodule update --init --recursive

# Navigate to NFC library directory
cd dependencies/linux_libnfc-nci

# Clean and configure
echo "⚙️  Configuring NFC build..."
make clean || true
./bootstrap || true
./configure --enable-shared --disable-static

# Build libraries
echo "🔨 Compiling NFC libraries..."
make -j$(nproc)

# Build Python module
echo "🐍 Building Python NFC module..."
cd python
./build.sh
cd ..

# Create temporary staging directory for archive
STAGING_DIR=$(mktemp -d)
echo "📦 Preparing NFC archive in $STAGING_DIR..."

# Copy shared libraries (.la files and any .so files)
if [ -f "libnfc_nci_linux.la" ]; then
    cp libnfc_nci_linux.la "$STAGING_DIR/"
fi
if [ -f "libpn7160_fw.la" ]; then
    cp libpn7160_fw.la "$STAGING_DIR/"
fi

# Copy any built .so files
find .libs -name "libnfc_nci_linux*.so*" -exec cp {} "$STAGING_DIR/" \; 2>/dev/null || true
find .libs -name "libpn7160_fw*.so*" -exec cp {} "$STAGING_DIR/" \; 2>/dev/null || true

# Copy executable (test app) - use the actual binary, not the libtool wrapper
if [ -f ".libs/nfcDemoApp" ]; then
    echo "Copying actual nfcDemoApp executable from .libs..."
    cp .libs/nfcDemoApp "$STAGING_DIR/"
elif [ -f "nfcDemoApp" ]; then
    echo "Warning: Using libtool wrapper script for nfcDemoApp (may not work standalone)"
    cp nfcDemoApp "$STAGING_DIR/"
fi

# Copy header files
if [ -f "src/include/linux_nfc_api.h" ]; then
    cp src/include/linux_nfc_api.h "$STAGING_DIR/"
fi
if [ -f "src/include/linux_nfc_factory_api.h" ]; then
    cp src/include/linux_nfc_factory_api.h "$STAGING_DIR/"
fi
if [ -f "src/include/linux_nfc_api_compatibility.h" ]; then
    cp src/include/linux_nfc_api_compatibility.h "$STAGING_DIR/"
fi

# Copy configuration files
if [ -f "conf/libnfc-nci.conf" ]; then
    cp conf/libnfc-nci.conf "$STAGING_DIR/"
fi
if [ -f "conf/libnfc-nxp.conf" ]; then
    cp conf/libnfc-nxp.conf "$STAGING_DIR/"
fi

# Copy pkg-config file
if [ -f "libnfc-nci.pc" ]; then
    cp libnfc-nci.pc "$STAGING_DIR/"
fi

# Copy Python native extension module
find python -name "nfc_native*.so" -exec cp {} "$STAGING_DIR/" \; 2>/dev/null || true

# Copy Python nfc_reader module
if [ -f "python/nfc_reader.py" ]; then
    cp python/nfc_reader.py "$STAGING_DIR/"
fi

# Create output directories
mkdir -p "$FLOWY_OUTPUT_DIR/libraries"

# Create the archive
echo "📦 Creating libnfc.tar.xz archive..."
cd "$STAGING_DIR"
tar -cJf "$FLOWY_OUTPUT_DIR/libraries/libnfc.tar.xz" *

# Clean up staging directory
rm -rf "$STAGING_DIR"

# Go back to project root
cd - > /dev/null
cd ../..

echo "✅ NFC libraries built and archived successfully!"
echo "   Archive: $FLOWY_OUTPUT_DIR/libraries/libnfc.tar.xz"
echo "   Contents:"
tar -tJf "$FLOWY_OUTPUT_DIR/libraries/libnfc.tar.xz" | sed 's/^/     /'
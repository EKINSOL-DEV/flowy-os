#!/bin/bash
# nfc.sh - Install NFC libraries and dependencies
# This script installs the custom-built NFC libraries for PN7160 chip support.
#
# Usage: Called from customize02 with chroot directory as parameter
#   ./nfc.sh $1
#
# $1 = chroot directory path

set -e

CHROOT_DIR="$1"

echo "Installing NFC libraries..."

# Install custom NFC libraries if they exist in the build output
if [ -n "$FLOWY_OUTPUT_DIR" ] && [ -f "$FLOWY_OUTPUT_DIR/libraries/libnfc_nci_linux.so" ] && [ -f "$FLOWY_OUTPUT_DIR/libraries/libpn7160_fw.so" ]; then
    echo "Installing custom NFC libraries to /usr/lib..."
    cp "$FLOWY_OUTPUT_DIR/libraries/libnfc_nci_linux.so" "$CHROOT_DIR/usr/lib/"
    cp "$FLOWY_OUTPUT_DIR/libraries/libpn7160_fw.so" "$CHROOT_DIR/usr/lib/"
    
    # Set proper permissions for shared libraries
    chmod 644 "$CHROOT_DIR/usr/lib/libnfc_nci_linux.so"
    chmod 644 "$CHROOT_DIR/usr/lib/libpn7160_fw.so"
    
    # Install Python module if it exists
    if [ -f "$FLOWY_OUTPUT_DIR/libraries/nfc_native.cpython-311-aarch64-linux-gnu.so" ]; then
        echo "Installing Python NFC extension module..."
        # Install to Python site-packages
        PYTHON_SITE_PACKAGES=$(chroot "$CHROOT_DIR" python3 -c "import site; print(site.getsitepackages()[0])")
        cp "$FLOWY_OUTPUT_DIR/libraries/nfc_native.cpython-311-aarch64-linux-gnu.so" "$CHROOT_DIR$PYTHON_SITE_PACKAGES/"
        chmod 644 "$CHROOT_DIR$PYTHON_SITE_PACKAGES/nfc_native.cpython-311-aarch64-linux-gnu.so"
        echo "✅ Python NFC extension module installed to $PYTHON_SITE_PACKAGES"
    fi
    
    # Install nfc_reader.py module if it exists
    if [ -f "$FLOWY_OUTPUT_DIR/python/nfc_reader.py" ]; then
        echo "Installing nfc_reader Python module..."
        PYTHON_SITE_PACKAGES=$(chroot "$CHROOT_DIR" python3 -c "import site; print(site.getsitepackages()[0])")
        
        # Copy nfc_reader module
        cp "$FLOWY_OUTPUT_DIR/python/nfc_reader.py" "$CHROOT_DIR$PYTHON_SITE_PACKAGES/"
        chmod 644 "$CHROOT_DIR$PYTHON_SITE_PACKAGES/nfc_reader.py"
        
        echo "✅ nfc_reader module installed to $PYTHON_SITE_PACKAGES"
    fi
    
    # Update library cache
    chroot "$CHROOT_DIR" ldconfig
    
    echo "✅ Custom NFC libraries installed to /usr/lib/"
else
    if [ -z "$FLOWY_OUTPUT_DIR" ]; then
        echo "⚠️  FLOWY_OUTPUT_DIR environment variable not set"
    else
        echo "⚠️  Custom NFC libraries not found in $FLOWY_OUTPUT_DIR/libraries"
    fi
    echo "   Libraries should be built automatically if missing during main build"
    echo "   Or run './build-kiosk.sh --build-nfc' to build them manually"
fi

# Add user to gpio group for GPIO access (needed for NFC reset/IRQ pins)
echo "Setting up NFC permissions..."
chroot "$CHROOT_DIR" usermod -a -G gpio "$IGconf_device_user1" || true

echo "NFC configuration completed."
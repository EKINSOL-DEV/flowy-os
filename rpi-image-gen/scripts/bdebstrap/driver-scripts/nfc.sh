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

# Install NFC configuration file if it exists
if [ -n "$FLOWY_OUTPUT_DIR" ] && [ -f "$FLOWY_OUTPUT_DIR/config/libnfc-nci.conf" ]; then
    echo "Installing NFC configuration file..."
    mkdir -p "$CHROOT_DIR/usr/local/etc"
    cp "$FLOWY_OUTPUT_DIR/config/libnfc-nci.conf" "$CHROOT_DIR/usr/local/etc/libnfc-nci.conf"
    chmod 644 "$CHROOT_DIR/usr/local/etc/libnfc-nci.conf"
    echo "✅ NFC configuration installed to /usr/local/etc/libnfc-nci.conf"
else
    echo "⚠️  NFC configuration file not found in $FLOWY_OUTPUT_DIR/config/"
fi

# Install custom NFC libraries from tar.xz archive
if [ -n "$FLOWY_OUTPUT_DIR" ] && [ -f "$FLOWY_OUTPUT_DIR/libraries/libnfc.tar.xz" ]; then
    echo "Installing custom NFC libraries from libnfc.tar.xz..."
    
    # Create temporary extraction directory
    TEMP_EXTRACT_DIR=$(mktemp -d)
    
    # Extract the archive
    echo "Extracting libnfc.tar.xz..."
    tar -xf "$FLOWY_OUTPUT_DIR/libraries/libnfc.tar.xz" -C "$TEMP_EXTRACT_DIR"
    
    # Create target directories (mimicking 'make install' structure)
    mkdir -p "$CHROOT_DIR/usr/local/lib"
    mkdir -p "$CHROOT_DIR/usr/local/sbin" 
    mkdir -p "$CHROOT_DIR/usr/local/include"
    mkdir -p "$CHROOT_DIR/usr/local/etc"
    mkdir -p "$CHROOT_DIR/usr/local/lib/pkgconfig"
    
    # Install shared libraries and create proper symlinks manually
    if [ -f "$TEMP_EXTRACT_DIR/libnfc_nci_linux.la" ]; then
        echo "Installing libnfc_nci_linux library..."
        cp "$TEMP_EXTRACT_DIR/libnfc_nci_linux.la" "$CHROOT_DIR/usr/local/lib/"
        
        # Copy .so files and create symlinks manually
        for sofile in "$TEMP_EXTRACT_DIR"/libnfc_nci_linux.so*; do
            if [ -f "$sofile" ]; then
                filename=$(basename "$sofile")
                cp "$sofile" "$CHROOT_DIR/usr/local/lib/"
                chmod 755 "$CHROOT_DIR/usr/local/lib/$filename"
                
                # Create symlinks (e.g., libname.so.0.0.0 -> libname.so.0 -> libname.so)
                case "$filename" in
                    *.so.*.*.*)
                        base=$(echo "$filename" | sed 's/\.so\..*//')
                        version=$(echo "$filename" | sed 's/.*\.so\.\([0-9]*\)\..*/\1/')
                        cd "$CHROOT_DIR/usr/local/lib"
                        ln -sf "$filename" "${base}.so.${version}" 2>/dev/null || true
                        ln -sf "${base}.so.${version}" "${base}.so" 2>/dev/null || true
                        cd - >/dev/null
                        ;;
                esac
            fi
        done
    fi
    
    if [ -f "$TEMP_EXTRACT_DIR/libpn7160_fw.la" ]; then
        echo "Installing libpn7160_fw library..."
        cp "$TEMP_EXTRACT_DIR/libpn7160_fw.la" "$CHROOT_DIR/usr/local/lib/"
        
        # Copy .so files and create symlinks manually
        for sofile in "$TEMP_EXTRACT_DIR"/libpn7160_fw.so*; do
            if [ -f "$sofile" ]; then
                filename=$(basename "$sofile")
                cp "$sofile" "$CHROOT_DIR/usr/local/lib/"
                chmod 755 "$CHROOT_DIR/usr/local/lib/$filename"
                
                # Create symlinks (e.g., libname.so.0.0.0 -> libname.so.0 -> libname.so)
                case "$filename" in
                    *.so.*.*.*)
                        base=$(echo "$filename" | sed 's/\.so\..*//')
                        version=$(echo "$filename" | sed 's/.*\.so\.\([0-9]*\)\..*/\1/')
                        cd "$CHROOT_DIR/usr/local/lib"
                        ln -sf "$filename" "${base}.so.${version}" 2>/dev/null || true
                        ln -sf "${base}.so.${version}" "${base}.so" 2>/dev/null || true
                        cd - >/dev/null
                        ;;
                esac
            fi
        done
    fi
    
    # Install test executable to /usr/local/sbin/ (comment out for production)
    if [ -f "$TEMP_EXTRACT_DIR/nfcDemoApp" ]; then echo "Installing nfcDemoApp test executable..."; cp "$TEMP_EXTRACT_DIR/nfcDemoApp" "$CHROOT_DIR/usr/local/sbin/"; chmod 755 "$CHROOT_DIR/usr/local/sbin/nfcDemoApp"; fi
    
    # Install header files to /usr/local/include/
    if [ -f "$TEMP_EXTRACT_DIR/linux_nfc_api.h" ]; then
        echo "Installing NFC header files..."
        cp "$TEMP_EXTRACT_DIR/linux_nfc_api.h" "$CHROOT_DIR/usr/local/include/"
        chmod 644 "$CHROOT_DIR/usr/local/include/linux_nfc_api.h"
    fi
    if [ -f "$TEMP_EXTRACT_DIR/linux_nfc_factory_api.h" ]; then
        cp "$TEMP_EXTRACT_DIR/linux_nfc_factory_api.h" "$CHROOT_DIR/usr/local/include/"
        chmod 644 "$CHROOT_DIR/usr/local/include/linux_nfc_factory_api.h"
    fi
    if [ -f "$TEMP_EXTRACT_DIR/linux_nfc_api_compatibility.h" ]; then
        cp "$TEMP_EXTRACT_DIR/linux_nfc_api_compatibility.h" "$CHROOT_DIR/usr/local/include/"
        chmod 644 "$CHROOT_DIR/usr/local/include/linux_nfc_api_compatibility.h"
    fi
    
    # Install configuration files to /usr/local/etc/
    if [ -f "$TEMP_EXTRACT_DIR/libnfc-nci.conf" ]; then
        echo "Installing NFC configuration files..."
        cp "$TEMP_EXTRACT_DIR/libnfc-nci.conf" "$CHROOT_DIR/usr/local/etc/"
        chmod 644 "$CHROOT_DIR/usr/local/etc/libnfc-nci.conf"
    fi
    if [ -f "$TEMP_EXTRACT_DIR/libnfc-nxp.conf" ]; then
        cp "$TEMP_EXTRACT_DIR/libnfc-nxp.conf" "$CHROOT_DIR/usr/local/etc/"
        chmod 644 "$CHROOT_DIR/usr/local/etc/libnfc-nxp.conf"
    fi
    
    # Install pkg-config file to /usr/local/lib/pkgconfig/
    if [ -f "$TEMP_EXTRACT_DIR/libnfc-nci.pc" ]; then
        echo "Installing pkg-config file..."
        cp "$TEMP_EXTRACT_DIR/libnfc-nci.pc" "$CHROOT_DIR/usr/local/lib/pkgconfig/"
        chmod 644 "$CHROOT_DIR/usr/local/lib/pkgconfig/libnfc-nci.pc"
    fi
    
    # Install Python module if it exists
    if [ -f "$TEMP_EXTRACT_DIR/nfc_native.cpython-311-aarch64-linux-gnu.so" ]; then
        echo "Installing Python NFC extension module..."
        
        # Install to system site-packages
        PYTHON_SITE_PACKAGES=$(chroot "$CHROOT_DIR" python3 -c "import site; print(site.getsitepackages()[0])")
        cp "$TEMP_EXTRACT_DIR/nfc_native.cpython-311-aarch64-linux-gnu.so" "$CHROOT_DIR$PYTHON_SITE_PACKAGES/"
        chmod 644 "$CHROOT_DIR$PYTHON_SITE_PACKAGES/nfc_native.cpython-311-aarch64-linux-gnu.so"
        echo "✅ Python NFC extension module installed to system: $PYTHON_SITE_PACKAGES"
        
        # Also install to the flowy server virtual environment
        VENV_SITE_PACKAGES="$CHROOT_DIR/flowy/server/.venv/lib/python3.11/site-packages"
        if [ -d "$VENV_SITE_PACKAGES" ]; then
            cp "$TEMP_EXTRACT_DIR/nfc_native.cpython-311-aarch64-linux-gnu.so" "$VENV_SITE_PACKAGES/"
            chmod 644 "$VENV_SITE_PACKAGES/nfc_native.cpython-311-aarch64-linux-gnu.so"
            echo "✅ Python NFC extension module also installed to venv: /flowy/server/.venv/lib/python3.11/site-packages"
        fi
    fi
    
    # Install nfc_reader.py module if it exists
    if [ -f "$TEMP_EXTRACT_DIR/nfc_reader.py" ]; then
        echo "Installing nfc_reader Python module..."
        
        # Install to system site-packages
        PYTHON_SITE_PACKAGES=$(chroot "$CHROOT_DIR" python3 -c "import site; print(site.getsitepackages()[0])")
        cp "$TEMP_EXTRACT_DIR/nfc_reader.py" "$CHROOT_DIR$PYTHON_SITE_PACKAGES/"
        chmod 644 "$CHROOT_DIR$PYTHON_SITE_PACKAGES/nfc_reader.py"
        echo "✅ nfc_reader module installed to system: $PYTHON_SITE_PACKAGES"
        
        # Also install to the flowy server virtual environment
        VENV_SITE_PACKAGES="$CHROOT_DIR/flowy/server/.venv/lib/python3.11/site-packages"
        if [ -d "$VENV_SITE_PACKAGES" ]; then
            cp "$TEMP_EXTRACT_DIR/nfc_reader.py" "$VENV_SITE_PACKAGES/"
            chmod 644 "$VENV_SITE_PACKAGES/nfc_reader.py"
            echo "✅ nfc_reader module also installed to venv: /flowy/server/.venv/lib/python3.11/site-packages"
        else
            echo "⚠️  Virtual environment not found at /flowy/server/.venv"
        fi
    fi
    
    # Clean up temporary directory
    rm -rf "$TEMP_EXTRACT_DIR"
    
    # Update library cache
    chroot "$CHROOT_DIR" ldconfig
    
    echo "✅ NFC libraries installed from libnfc.tar.xz to /usr/local/"
else
    if [ -z "$FLOWY_OUTPUT_DIR" ]; then
        echo "⚠️  FLOWY_OUTPUT_DIR environment variable not set"
    else
        echo "⚠️  libnfc.tar.xz not found in $FLOWY_OUTPUT_DIR/libraries/"
    fi
    echo "   Archive should be built automatically if missing during main build"
    echo "   Or run './build-kiosk.sh --build-nfc' to build it manually"
fi

# Add user to gpio group for GPIO access (needed for NFC reset/IRQ pins)
echo "Setting up NFC permissions..."
chroot "$CHROOT_DIR" usermod -a -G gpio "$IGconf_device_user1" || true

echo "NFC configuration completed."
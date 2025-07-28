# FlowOS Build Instructions

This document provides instructions for building the FlowOS Raspberry Pi image using the build system.

## Prerequisites

- **Build Environment**: Ubuntu/Linux development machine with ARM64 architecture
- **Target Hardware**: Raspberry Pi (CM4/CM5/Pi4/Pi5)
- **Dependencies**: All required build dependencies are installed via the build system
- **Permissions**: The builder user must have sudo access for cleanup operations

## Quick Start

```bash
# Navigate to project directory
cd ~/flowy-os

# Standard build
./build-kiosk.sh

# Build with NFC library rebuild (when NFC dependencies change)
./build-kiosk.sh --build-nfc

# View all options
./build-kiosk.sh --help
```

## Build Script Options

The `build-kiosk.sh` script supports the following arguments:

| Option | Description |
|--------|-------------|
| `--build-nfc` | Rebuild NFC libraries from the git submodule before building the image |
| `--help`, `-h` | Show usage information and available options |

### NFC Library Building

The `--build-nfc` option:
1. Updates the `linux_libnfc-nci` git submodule (64bit_rpi_fixes branch)
2. Configures and compiles the NFC libraries with 64-bit ARM fixes
3. Copies the built libraries to `output/libraries/`
4. Proceeds with the normal image build process

Use this option when:
- First time building the project
- NFC library dependencies have been updated
- You need fresh NFC library builds

## Build Process Details

The build script performs these operations:

1. **Optional NFC Build** (if `--build-nfc` specified):
   - Updates git submodules
   - Builds `libnfc_nci_linux-1.so.0.0.0` and `libpn7160_fw.so.0.0.0`
   - Copies libraries to `output/libraries/`

2. **Image Build**:
   - Cleans previous build artifacts from `rpi-image-gen/work`
   - Creates the `output/images` directory
   - Backs up previous image (`latest.img` → `prev.img`)
   - Executes the underlying build system with webkiosk configuration
   - Moves completed image to `output/images/latest.img`

### 4. Build Configuration

The build uses the following configuration:
- **Base Config**: `generic64-apt-simple` (64-bit ARM Debian-based)
- **Custom Layer**: `webkiosk` (located in `rpi-image-gen/webkiosk/`)
- **Image Options**: `rpi-image-gen/webkiosk/image.options`

## Output Files

Upon successful completion, the build generates:

### Images
- **Primary Image**: `output/images/latest.img` - The flashable Raspberry Pi image
- **Backup Image**: `output/images/prev.img` - Previous build (if exists)

### Libraries (when using --build-nfc)
- **NFC Main Library**: `output/libraries/libnfc_nci_linux-1.so.0.0.0` - Core NFC functionality
- **PN7160 Firmware**: `output/libraries/libpn7160_fw.so.0.0.0` - Hardware-specific firmware

### Build Artifacts
- **Debug Files**: `rpi-image-gen/work/*/artefacts/` - Build intermediates and debugging files

### Downloading Images

A web server runs on port 80 providing easy access to download the built images:

- **Latest Image**: `http://<server-address>/output/images/latest.img`
- **Previous Image**: `http://<server-address>/output/images/prev.img`

This allows convenient downloading of images without needing SSH/SCP access.

## Image Features

The built image includes:
- **Base System**: Debian Bookworm ARM64
- **WiFi Management**: NetworkManager-based WiFi connectivity with web interface
- **Kiosk Mode**: Full-screen web kiosk functionality
- **Custom Services**: WiFi configuration API and web interface
- **Hardware Support**: Raspberry Pi CM4/CM5/Pi4/Pi5 optimized

## Troubleshooting

### Build Failures
- Ensure sufficient disk space (minimum 8GB free, but this shouldn't be a problem)
- Check that all dependencies are installed
- Verify network connectivity for package downloads

### Permission Issues
- The build script uses `sudo` for cleanup operations
- Ensure the builder user has appropriate sudo permissions

### Clean Build
To perform a completely clean build (removes previous images):
```bash
sudo rm -rf output/images/
./build-kiosk.sh
```

### NFC Library Dependencies
The project includes NFC functionality via the `linux_libnfc-nci` git submodule:
- **Location**: `dependencies/linux_libnfc-nci/`
- **Branch**: `64bit_rpi_fixes` (includes ARM64 compatibility fixes)
- **Libraries**: Builds to `libnfc_nci_linux` and `libpn7160_fw` shared objects

To update NFC dependencies:
```bash
git submodule update --remote dependencies/linux_libnfc-nci
./build-kiosk.sh --build-nfc
```

## Build System Details

The build system is based on a custom Debian image generator that:
- Uses `bdebstrap` for creating the base Debian system
- Applies hardware-specific configurations for Raspberry Pi
- Integrates custom applications and services
- Generates bootable disk images with proper partitioning
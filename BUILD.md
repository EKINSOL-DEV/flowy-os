# FlowOS Build Instructions

This document provides instructions for building the FlowOS Raspberry Pi image using the build system.

## Prerequisites

- **Build Environment**: Ubuntu/Linux development machine with the "builder" user
- **Target Hardware**: Raspberry Pi (CM4/CM5/Pi4/Pi5)
- **Dependencies**: All required build dependencies are installed via the build system

## Build Process

### 1. Connect to the Build Server

The build must be executed on the remote server as the "builder" user:

```bash
# Connect to the build server
ssh builder@<server-address>
```

### 2. Navigate to the Project Directory

```bash
cd ~/flowy-os
```

### 3. Execute the Build

Run the automated build script:

```bash
./build-kiosk.sh
```

The build script performs the following operations:
- Cleans any previous build artifacts from `rpi-image-gen/work`
- Creates the `images` directory if it doesn't exist
- Backs up the previous image (moves `latest.img` to `prev.img`)
- Executes the underlying build system with the webkiosk configuration
- Moves the completed image to `images/latest.img`

### 4. Build Configuration

The build uses the following configuration:
- **Base Config**: `generic64-apt-simple` (64-bit ARM Debian-based)
- **Custom Layer**: `webkiosk` (located in `rpi-image-gen/webkiosk/`)
- **Image Options**: `rpi-image-gen/webkiosk/image.options`

## Output Files

Upon successful completion, the build generates:

- **Primary Image**: `images/latest.img` - The flashable Raspberry Pi image
- **Backup Image**: `images/prev.img` - Previous build (if exists)
- **Build Artifacts**: `rpi-image-gen/work/*/artefacts/` - Build intermediates and debugging files

### Downloading Images

A web server runs on port 80 providing easy access to download the built images:

- **Latest Image**: `http://<server-address>/latest.img`
- **Previous Image**: `http://<server-address>/prev.img`

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
- Ensure sufficient disk space (minimum 8GB free, but this shouldn't be a problem if you're running this on a server)
- Check that all dependencies are installed
- Verify network connectivity for package downloads

### Permission Issues
- The build script uses `sudo` for cleanup operations
- Ensure the builder user has appropriate sudo permissions

### Clean Build
To perform a completely clean build (removes previous images):
```bash
sudo rm -rf images/
./build-kiosk.sh
```

## Build System Details

The build system is based on a custom Debian image generator that:
- Uses `bdebstrap` for creating the base Debian system
- Applies hardware-specific configurations for Raspberry Pi
- Integrates custom applications and services
- Generates bootable disk images with proper partitioning
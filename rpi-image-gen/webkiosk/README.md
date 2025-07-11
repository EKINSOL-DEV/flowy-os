# Flowy OS WebKiosk for Raspberry Pi

A lightweight, secure web kiosk system for Raspberry Pi devices, built on top of Debian with Wayland/Cage compositor and Chromium browser. Perfect for digital signage, information terminals, interactive displays, and dedicated web applications.

## Overview

The Flowy OS WebKiosk creates a locked-down Raspberry Pi image that automatically boots into a fullscreen web browser displaying your chosen web application. It includes:

- **Minimal Wayland Environment**: Uses Cage compositor for lightweight, secure kiosk operation
- **Chromium Browser**: Configured for kiosk mode with security hardening
- **FastAPI Backend**: Included web server for local applications
- **Remote Management**: SSH access for administration
- **Emergency Escape**: Keyboard shortcut (Ctrl+Shift+K) to disable kiosk mode

## System Requirements

### Hardware
- Raspberry Pi 4, 5, CM4, CM5, or Zero 2W
- Minimum 4GB SD card (8GB+ recommended)
- 1GB+ RAM recommended
- HDMI display

### Build System
- Linux host system (Debian/Ubuntu recommended)
- Root/sudo access for image building
- Dependencies installed via `install_deps.sh`

## Quick Start

### Building the Image

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/flowy-os.git
   cd flowy-os/rpi-image-gen
   ```

2. **Install dependencies**:
   ```bash
   sudo ./install_deps.sh
   ```

3. **Build the kiosk image**:
   ```bash
   sudo ./build.sh -c generic64-apt-simple -D ./webkiosk/ -o ./webkiosk/image.options
   ```

4. **Flash to SD card**:
   ```bash
   # Replace /dev/sdX with your SD card device
   sudo dd if=output/flowy-kiosk-test.img of=/dev/sdX bs=4M status=progress
   sync
   ```

### First Boot

1. Insert SD card and power on Raspberry Pi
2. System automatically boots into kiosk mode
3. Default display: FastAPI documentation at http://localhost:8080/docs
4. SSH access: `ssh flowy@flowpi` (password: `demo`)

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi Boot                     │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   systemd Services                       │
│  ┌─────────────────┐        ┌────────────────────────┐ │
│  │ kiosk.service   │        │ kioskserver.service    │ │
│  │ (Cage+Chromium) │        │ (FastAPI Backend)      │ │
│  └────────┬────────┘        └───────────┬────────────┘ │
└───────────┼──────────────────────────────┼──────────────┘
            │                              │
            │         ┌────────────────────▼──────┐
            │         │ localhost:8080           │
            │         │ Web Application          │
            │         └────────────▲──────────────┘
            │                      │
            └──────────────────────┘
```

### Key Components

#### 1. **Build System Integration** (`build.sh`)
- Leverages rpi-image-gen's modular build system
- Uses `generic64-apt-simple` as base configuration
- Applies webkiosk-specific customizations

#### 2. **Customization Script** (`bdebstrap/customize01`)
- Installs required packages (cage, chromium, python3)
- Configures systemd services
- Sets up emergency kill switch
- Deploys web application

#### 3. **Backend Server** (`flowy-image-server/`)
- FastAPI-based web application
- Runs on port 8080
- Easily customizable for your needs

#### 4. **Service Configuration** (`services/`)
- **kiosk.service**: Manages Cage/Chromium
- **kioskserver.service**: Manages web backend
- Both configured for automatic restart

## Customization Guide

### Changing the Displayed Website

#### Option 1: External Website
Edit `services/kiosk.service.tpl` and change the URL:
```bash
ExecStart=/usr/bin/cage -- /usr/bin/chromium --kiosk https://your-website.com
```

#### Option 2: Custom Local Application
Replace the FastAPI application in `flowy-image-server/` with your own:
```python
# flowy-image-server/main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Your Kiosk App</title>
        </head>
        <body>
            <h1>Welcome to Your Kiosk</h1>
        </body>
    </html>
    """
```

### Adding System Packages

Edit `bdebstrap/customize01` to install additional packages:
```bash
# Add your packages here
SYSTEM_PACKAGES="$SYSTEM_PACKAGES your-package-name"
```

### Configuring Network

Create a network configuration in your customization:
```bash
# In bdebstrap/customize01
cat > "$ROOT/etc/systemd/network/20-wired.network" <<EOF
[Match]
Name=eth0

[Network]
DHCP=yes
EOF
```

### Security Hardening

1. **Change default credentials** in `image.options`:
   ```bash
   USER_NAME="your-user"
   USER_PASS="strong-password"
   ```

2. **Disable SSH** (remove from `image.options`):
   ```bash
   # Comment out or remove:
   # ENABLE_SSH="your-user"
   ```

3. **Remove emergency kill switch** (edit `bdebstrap/customize01`):
   ```bash
   # Comment out the triggerhappy configuration
   ```

## Development Workflow

### Local Testing

1. **Set up development environment**:
   ```bash
   cd webkiosk/flowy-image-server
   python3 -m venv venv
   source venv/bin/activate
   pip install -r ../pyreqs.txt
   ```

2. **Run locally**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8080
   ```

3. **Test in browser**:
   Open http://localhost:8080

### Rapid Iteration

For faster development cycles:

1. **Use SSH to update running kiosk**:
   ```bash
   # Copy new application
   scp -r flowy-image-server/ flowy@flowpi:~/
   
   # Restart service
   ssh flowy@flowpi 'sudo systemctl restart kioskserver'
   ```

2. **Reload browser**:
   ```bash
   ssh flowy@flowpi 'sudo systemctl restart kiosk'
   ```

## Troubleshooting

### Black Screen on Boot
- Check HDMI connection
- Verify display compatibility
- Review logs: `ssh flowy@flowpi 'journalctl -u kiosk'`

### Web Application Not Loading
- Check backend service: `systemctl status kioskserver`
- Verify port 8080: `netstat -tlnp | grep 8080`
- Review application logs: `journalctl -u kioskserver`

### Cannot SSH Into Device
- Ensure device is on network: Check router DHCP leases
- Default hostname: `flowpi`
- Try IP directly if hostname resolution fails

### Emergency Access
If kiosk is unresponsive:
1. Press Ctrl+Shift+K to disable kiosk
2. Switch to TTY2-6: Ctrl+Alt+F2
3. Login with credentials

## Security Considerations

### Default Security Features
- Non-root user execution
- Minimal system packages
- No X11 (Wayland only)
- Chromium security flags enabled

### Recommended Hardening
1. Change all default passwords
2. Use key-based SSH authentication
3. Configure firewall rules
4. Disable unnecessary services
5. Regular security updates

### Network Isolation
For high-security deployments:
- Use separate VLAN for kiosks
- Implement content filtering
- Disable outbound internet (local only)

## Advanced Configuration

### Multi-Display Support
```bash
# In kiosk.service
Environment="WAYLAND_DISPLAY=wayland-1"
Environment="WLR_DRM_DEVICES=/dev/dri/card0:/dev/dri/card1"
```

### Touch Screen Calibration
```bash
# Add to customize01
cat > "$ROOT/etc/udev/rules.d/99-touchscreen.rules" <<EOF
ATTRS{name}=="Your Touch Device", ENV{LIBINPUT_CALIBRATION_MATRIX}="1 0 0 0 1 0"
EOF
```

### Performance Tuning
```bash
# GPU memory split (config.txt)
gpu_mem=128

# Chromium flags for low-memory devices
--disable-gpu-sandbox --disable-software-rasterizer
```

## Contributing

### Reporting Issues
- Use GitHub Issues for bug reports
- Include: Pi model, build command, error logs
- Attach `journalctl` output when relevant

### Development Guidelines
1. Test on multiple Pi models
2. Document all changes
3. Follow existing code style
4. Update this README for new features

## License

This project inherits the license from the parent Flowy OS project. See LICENSE file in the repository root.

## Support

- Documentation: This README
- Issues: GitHub Issues
- Community: [Discord/Forum link]

---

Built with ❤️ for the Raspberry Pi community
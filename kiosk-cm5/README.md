# Kiosk CM5 - Multi-Service Raspberry Pi Kiosk OS

A complete, offline-first kiosk operating system for Raspberry Pi CM5 with NFC support, WiFi management, and multiple Python API services.

## Features

- **Offline-First Operation**: Fully functional without internet connectivity
- **WiFi Management**: Built-in network scanning and connection interface
- **NFC Integration**: Real-time NFC card detection with WebSocket communication
- **Multi-Service Architecture**: Multiple Python APIs and Docker containers
- **Auto-Updates**: Git-based update system with rollback capability
- **Security Hardened**: Locked-down kiosk environment with minimal attack surface

## Quick Start

### Prerequisites

- 64-bit Raspberry Pi OS or Ubuntu host system
- 32GB+ SD card for deployment
- sudo access for building

### Build the Image

1. **Clone rpi-image-gen**:
```bash
git clone https://github.com/raspberrypi/rpi-image-gen.git
cd rpi-image-gen
sudo ./install_deps.sh
```

2. **Copy kiosk-cm5 configuration**:
```bash
cp -r /path/to/kiosk-cm5 ./examples/
```

3. **Build the image**:
```bash
sudo ./examples/kiosk-cm5/build.sh
```

### Deploy the Image

1. **Flash to SD card**:
```bash
# Find your SD card device
lsblk

# Flash the image (replace /dev/sdX with your SD card)
sudo dd if=work/kiosk-multi-service/artefacts/*.img of=/dev/sdX bs=4M status=progress
```

2. **Boot the device**: Insert SD card into Raspberry Pi CM5 and power on

## System Architecture

```
┌─────────────────┐
│   Kiosk Browser │ ──────┐
│ (Frontend UI)   │       │
└─────────────────┘       │
                          ▼
┌─────────────────┐   ┌─────────────────┐
│     nginx       │   │   Python APIs   │
│ (Reverse Proxy) │◄──┤ - NFC Service   │
└─────────────────┘   │ - Network API   │
          │           │ - Update API    │
          ▼           └─────────────────┘
┌─────────────────┐   ┌─────────────────┐
│ Docker Services │   │   System Mgmt   │
│ - PostgreSQL    │   │ - Health Monitor │
│ - Redis         │   │ - Log Aggregator │
│ - Prometheus    │   │ - Auto-updater  │
└─────────────────┘   └─────────────────┘
```

## Network Configuration

- **Port 80**: nginx (frontend + API proxy)
- **Port 3001**: NFC WebSocket service
- **Port 3002**: NFC REST API
- **Port 3003**: Network Management API
- **Port 22**: SSH (restricted access)
- **Internal Ports**: Docker services (PostgreSQL, Redis, etc.)

## First Boot Sequence

1. **System boots** into kiosk mode
2. **Network check** - if no connection, shows WiFi setup
3. **WiFi setup screen** allows network scanning and connection
4. **Services start** - NFC, APIs, Docker containers
5. **Main application** loads with NFC reader interface

## WiFi Setup (Offline Mode)

When no network is available:

1. System shows **Network Setup** screen
2. Click **"Scan Networks"** to find available WiFi
3. Select network and enter password
4. System connects and transitions to online mode
5. All services become available

## NFC Integration

### Supported Readers
- PN532 (USB/UART)
- ACR122U (USB)
- Any libnfc-compatible reader

### Real-time Events
- **Card Detection**: Instant WebSocket notification to frontend
- **Card Removal**: Automatic cleanup and notification
- **Multiple Formats**: Support for various NFC card types

### WebSocket Protocol
```javascript
// Connect to NFC WebSocket
const ws = new WebSocket('ws://localhost/ws');

ws.onmessage = (event) => {
    const nfcEvent = JSON.parse(event.data);
    // Handle: nfc_detected, nfc_removed
};
```

## API Endpoints

### Network Management API
```
GET  /api/network/scan          # Scan for WiFi networks
POST /api/network/connect       # Connect to network
GET  /api/network/status        # Connection status
POST /api/network/disconnect    # Disconnect from network
DELETE /api/network/forget/{ssid} # Remove saved network
```

### System Health
```
GET /health                     # System health check
GET /api/network/connectivity   # Internet connectivity test
```

## Update System

### Automatic Updates
- **Hourly checks** for repository updates
- **Git-based** application updates
- **Docker image** updates for containers
- **Rollback capability** if updates fail

### Manual Updates
```bash
# Check for updates
sudo /opt/kiosk/scripts/update.sh check

# Apply updates
sudo /opt/kiosk/scripts/update.sh update

# Force rollback
sudo /opt/kiosk/scripts/update.sh restore
```

## Configuration

### Environment Configuration
Edit `/opt/kiosk/config/environment.yml`:

```yaml
kiosk:
  mode: production
  update_interval: 3600
  wifi:
    auto_connect: true
    fallback_ssid: "KioskSetup"
  nfc:
    enabled: true
    timeout: 5000
```

### Service Configuration
- **systemd services**: `/etc/systemd/system/kiosk-*.service`
- **nginx config**: `/etc/nginx/sites-available/kiosk`
- **Docker services**: `/opt/kiosk/docker-compose.yml`

## Development

### Frontend Development
```bash
# Frontend files location
/opt/kiosk/frontend/
├── index.html      # Main application
├── css/app.css     # Styles
├── js/app.js       # Application logic
└── sw.js           # Service worker (offline support)
```

### Adding APIs
1. Create new Python service in `/opt/kiosk/apis/`
2. Add systemd service file
3. Update nginx configuration for routing
4. Restart services

### Custom Docker Services
1. Add service to `docker-compose.yml`
2. Configure networking and volumes
3. Update health checks

## Troubleshooting

### Common Issues

**1. NFC not working**
```bash
# Check NFC device
lsusb | grep -i nfc
systemctl status kiosk-nfc.service
```

**2. Network connection issues**
```bash
# Check NetworkManager
systemctl status NetworkManager
nmcli device status
```

**3. Services not starting**
```bash
# Check service logs
journalctl -u kiosk-nfc.service -f
journalctl -u kiosk-network.service -f
```

**4. Frontend not loading**
```bash
# Check nginx and frontend service
systemctl status nginx
systemctl status kiosk-frontend.service
curl http://localhost/health
```

### Logs and Monitoring
- **System logs**: `journalctl -f`
- **Application logs**: `/opt/kiosk/logs/`
- **Update logs**: `/var/log/kiosk-update.log`
- **Health status**: `curl http://localhost/health`

## Security

### Hardening Features
- **Restricted SSH**: Key-based authentication only
- **Firewall**: UFW with minimal open ports
- **User permissions**: Limited kiosk user privileges
- **Browser security**: Sandboxed chromium with disabled features
- **Auto-updates**: Signed commits and rollback capability

### Security Best Practices
1. Change default passwords
2. Use SSH keys instead of passwords
3. Regular security updates
4. Monitor system logs
5. Restrict physical access

## Hardware Requirements

### Minimum Requirements
- Raspberry Pi CM5 (4GB RAM recommended)
- 32GB SD card (Class 10 or better)
- NFC reader (PN532 or ACR122U)
- Display with HDMI connection

### Recommended Requirements
- Raspberry Pi CM5 with 8GB RAM
- 64GB SD card (SSD for production)
- High-quality NFC reader
- Touch display for interaction

## Support and Contributing

### Getting Help
- Check troubleshooting section above
- Review system logs for errors
- Test individual components

### Contributing
1. Fork the repository
2. Create feature branch
3. Test changes thoroughly
4. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on Raspberry Pi's rpi-image-gen
- Uses nginx for reverse proxy
- NFC integration via libnfc
- Frontend uses modern web standards for offline support
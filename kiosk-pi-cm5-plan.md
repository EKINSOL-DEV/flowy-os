# Kiosk Raspberry Pi CM5 OS Plan

## Architecture Overview

**Multi-Service Kiosk System** that combines:
- **Kiosk Frontend**: Web-based UI displayed in fullscreen browser
- **Python API Services**: Multiple FastAPI/Flask services 
- **Docker Containers**: Containerized services and applications
- **Reverse Proxy**: nginx for routing and load balancing
- **Service Management**: systemd for service orchestration

## System Components

### 1. Base OS Configuration
- Extend `generic64-apt-simple.cfg` from rpi-image-gen
- Install Docker, Python 3.11+, nginx, chromium
- Configure auto-login and kiosk mode

### 2. Service Architecture
```
┌─────────────────┐
│   Kiosk Browser │ ──────┐
│ (Frontend UI)   │       │
└─────────────────┘       │
                          ▼
┌─────────────────┐   ┌─────────────────┐
│     nginx       │   │   Python APIs   │
│ (Reverse Proxy) │◄──┤ - User API      │
└─────────────────┘   │ - Device API    │
          │           │ - Config API    │
          ▼           └─────────────────┘
┌─────────────────┐   ┌─────────────────┐
│ Docker Containers│   │   System Mgmt   │
│ - Database      │   │ - Health Monitor │
│ - Cache (Redis) │   │ - Log Aggregator │
│ - Custom Services│   │ - Auto-updater  │
└─────────────────┘   └─────────────────┘
```

### 3. Directory Structure
```
/opt/kiosk/
├── apis/          # Python API services
├── frontend/      # Web frontend files
├── docker/        # Docker compose files
├── config/        # Configuration files
├── scripts/       # Management scripts
└── logs/          # Application logs
```

### 4. Key Features
- **Auto-boot to kiosk**: Chromium in fullscreen mode
- **Multi-API hosting**: Each API runs as separate service
- **Container orchestration**: Docker Compose for complex services
- **Health monitoring**: Automatic service restart on failure
- **Remote management**: SSH access with security controls
- **Auto-updates**: Pull and deploy updates automatically

### 5. Network Configuration
- **Port 80/443**: nginx (frontend + API proxy)
- **Port 3000-3010**: Python APIs (internal)
  - **Port 3001**: NFC WebSocket service
  - **Port 3002**: NFC REST API
  - **Port 3003**: Network Management API
- **Port 5000-5010**: Docker services (internal)
- **Port 22**: SSH (restricted access)

## Implementation Tasks

### High Priority
1. ✅ Research and analyze the base rpi-image-gen system and webkiosk example structure
2. ⏳ Design overall system architecture for multi-service kiosk (APIs, frontend, Docker)
3. ⏳ Create base configuration file extending generic64-apt-simple.cfg
4. ⏳ Configure Docker installation and auto-start in the OS image
5. ⏳ Set up Python runtime environment with required dependencies

### Medium Priority
6. ⏳ Design and implement structure for hosting multiple Python APIs
7. ⏳ Configure web server (nginx/apache) for frontend hosting
8. ⏳ Configure kiosk browser to display the frontend application
9. ⏳ Create systemd services for API services, frontend, and Docker containers
10. ⏳ Configure networking, port management, and service discovery
11. ⏳ Implement security measures for kiosk environment

### Low Priority
12. ⏳ Design automatic update mechanism for applications and containers
13. ⏳ Set up monitoring, logging, and health checks for all services
14. ⏳ Create build scripts and documentation for the complete system

## Build Process

Based on the rpi-image-gen webkiosk example, the build command will be:
```bash
./build.sh -c kiosk-multi-service -D ./examples/kiosk-cm5/
```

## NFC Integration Architecture

### Real-time Communication Stack
```
NFC Reader → NFC API → WebSocket → Frontend
```

### Components

**NFC Service** (`/opt/kiosk/apis/nfc_service.py`):
- Continuous NFC monitoring using `nfcpy`
- WebSocket broadcasting to connected clients
- Event-driven architecture for instant response

**WebSocket Configuration** (nginx):
```nginx
location /ws {
    proxy_pass http://localhost:3001;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**Frontend Integration**:
```javascript
const ws = new WebSocket('ws://localhost/ws');
ws.onmessage = (event) => {
    const nfcEvent = JSON.parse(event.data);
    // Handle NFC detected/removed events
};
```

### NFC Message Format
```json
{
  "event": "nfc_detected|nfc_removed",
  "timestamp": "2025-01-26T10:30:00Z",
  "uid": "04:52:3A:B1:2C:80:00",
  "data": "optional_tag_data"
}
```

### Hardware Requirements
- NFC reader (PN532, ACR122U, or compatible)
- Install `libnfc` and Python `nfcpy` in base image
- USB/SPI connection to Raspberry Pi CM5

## Offline-First Architecture

### Network State Management
```
Boot → Check Network → Offline Mode → WiFi Setup → Online Mode
```

### Offline Frontend Features
**Embedded Resources**:
- All CSS/JS/images bundled locally
- Service Worker for offline caching
- Local storage for configuration and data
- No external CDN dependencies

**WiFi Management Interface**:
- Network scanner UI
- WPA/WPA2 credential input
- Connection status display
- Saved networks management

### WiFi Management API

**Network Service** (`/opt/kiosk/apis/network_service.py`):
```python
# WiFi scanning and connection management
import subprocess, json
from fastapi import FastAPI

class NetworkManager:
    def scan_networks(self):
        # nmcli dev wifi list
    def connect_network(self, ssid, password):
        # nmcli dev wifi connect
    def get_status(self):
        # Network connection state
```

**API Endpoints**:
- `GET /api/network/scan` - Available WiFi networks
- `POST /api/network/connect` - Connect to network
- `GET /api/network/status` - Connection status
- `DELETE /api/network/forget/{ssid}` - Remove saved network

### Network State Detection
```javascript
// Frontend network state management
class NetworkManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.setupEventListeners();
    }
    
    async checkConnectivity() {
        try {
            await fetch('/api/network/status');
            return true;
        } catch {
            return false;
        }
    }
}
```

### Offline Mode UI
- **Setup Screen**: WiFi configuration interface
- **Status Indicator**: Network connection state
- **Local Operations**: All core functions work offline
- **Sync Queue**: Store actions for when online

## Image Build and Deployment Process

### Prerequisites Setup
- **Host Requirements**: 64-bit Raspberry Pi OS or Ubuntu
- **Dependencies**: `sudo ./install_deps.sh` in rpi-image-gen
- **Storage**: 32GB+ SD card for deployment

### Project Structure
```
examples/kiosk-cm5/
├── bdebstrap/
│   ├── customize01           # System packages & Docker
│   ├── customize02           # Python environment & NFC libs
│   └── customize03           # Services & configuration
├── overlays/
│   └── opt/kiosk/           # Complete application stack
│       ├── frontend/        # Offline-first web app
│       ├── apis/           # Python services
│       ├── config/         # Configuration files
│       └── scripts/        # Management utilities
├── kiosk-multi-service.cfg  # Base system configuration
├── services/               # Systemd service templates
├── nginx.conf              # Reverse proxy config
├── docker-compose.yml      # Container orchestration
├── build.sh               # Image build script
├── deploy.sh              # Deployment utilities
└── update.sh              # Update mechanism
```

### Build Process
```bash
# Clone and setup rpi-image-gen
git clone https://github.com/raspberrypi/rpi-image-gen.git
cd rpi-image-gen
sudo ./install_deps.sh

# Build kiosk image
./build.sh -c kiosk-multi-service -D ./examples/kiosk-cm5/
```

## Update System Architecture

### Over-the-Air Updates
- **Git-based updates**: Pull application code from repository
- **Docker updates**: Automated container image updates
- **System updates**: APT packages with staged rollback
- **Configuration sync**: Environment-specific settings

### Update Components
```python
# /opt/kiosk/scripts/updater.py
class UpdateManager:
    def check_for_updates(self):
        # Check git repo, docker registry, apt
    def apply_updates(self):
        # Staged update with rollback capability
    def rollback(self):
        # Restore previous working state
```

## Frontend Implementation Guide

### Offline-First Architecture
```javascript
// Service Worker for offline caching
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('kiosk-v1').then((cache) => {
            return cache.addAll([
                '/',
                '/css/app.css',
                '/js/app.js',
                '/assets/images/'
            ]);
        })
    );
});

// Network state management
class NetworkManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.setupEventListeners();
        this.checkConnectivity();
    }
    
    setupEventListeners() {
        window.addEventListener('online', () => this.goOnline());
        window.addEventListener('offline', () => this.goOffline());
    }
}
```

### WiFi Management UI
```javascript
// WiFi configuration interface
class WiFiManager {
    async scanNetworks() {
        const response = await fetch('/api/network/scan');
        return response.json();
    }
    
    async connectToNetwork(ssid, password) {
        return fetch('/api/network/connect', {
            method: 'POST',
            body: JSON.stringify({ ssid, password })
        });
    }
}
```

### NFC Integration
```javascript
// Real-time NFC event handling
class NFCHandler {
    constructor() {
        this.ws = new WebSocket('ws://localhost/ws');
        this.setupWebSocket();
    }
    
    setupWebSocket() {
        this.ws.onmessage = (event) => {
            const nfcEvent = JSON.parse(event.data);
            this.handleNFCEvent(nfcEvent);
        };
    }
    
    handleNFCEvent(event) {
        switch(event.event) {
            case 'nfc_detected':
                this.onNFCDetected(event.uid, event.data);
                break;
            case 'nfc_removed':
                this.onNFCRemoved(event.uid);
                break;
        }
    }
}
```

## Backend Services Implementation

### NFC Service
```python
# /opt/kiosk/apis/nfc_service.py
import asyncio
import websockets
import json
from nfcpy import ContactlessFrontend

class NFCService:
    def __init__(self):
        self.clients = set()
        self.clf = ContactlessFrontend('usb')
        
    async def nfc_monitor(self):
        while True:
            tag = self.clf.connect(rdwr={'on-connect': self.on_tag_connect})
            if tag:
                await self.broadcast_event('nfc_detected', tag.identifier)
            else:
                await self.broadcast_event('nfc_removed', None)
            await asyncio.sleep(0.1)
    
    async def broadcast_event(self, event_type, uid):
        message = json.dumps({
            'event': event_type,
            'uid': uid.hex() if uid else None,
            'timestamp': datetime.now().isoformat()
        })
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )
```

### Network Management API
```python
# /opt/kiosk/apis/network_service.py
import subprocess
import json
from fastapi import FastAPI, HTTPException

app = FastAPI()

class NetworkManager:
    def scan_networks(self):
        result = subprocess.run(['nmcli', 'dev', 'wifi', 'list'], 
                              capture_output=True, text=True)
        # Parse and return network list
        
    def connect_network(self, ssid: str, password: str):
        result = subprocess.run([
            'nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password
        ], capture_output=True, text=True)
        return result.returncode == 0

@app.get("/api/network/scan")
async def scan_networks():
    networks = NetworkManager().scan_networks()
    return {"networks": networks}

@app.post("/api/network/connect")
async def connect_network(request: ConnectionRequest):
    success = NetworkManager().connect_network(request.ssid, request.password)
    if not success:
        raise HTTPException(status_code=400, detail="Connection failed")
    return {"status": "connected"}
```

## Deployment Methods

### Initial Deployment
```bash
# Flash image to SD card
sudo dd if=kiosk-cm5.img of=/dev/sdX bs=4M status=progress

# Or use Raspberry Pi Imager
rpi-imager --cli kiosk-cm5.img /dev/sdX
```

### Remote Updates
```bash
# Update script on device
#!/bin/bash
# /opt/kiosk/scripts/update.sh
cd /opt/kiosk
git pull origin main
docker-compose pull
systemctl restart kiosk-services
```

### Configuration Management
```yaml
# /opt/kiosk/config/environment.yml
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

This plan creates a robust, maintainable kiosk system that can scale from simple displays to complex multi-service applications with real-time NFC interaction, full offline capability, and comprehensive update mechanisms.
# Flowy Unified API

A modular API system using a "cogs" architecture where each service (LED, NFC, WiFi, etc.) is a separate module with isolated error handling. Individual cog failures don't crash the main server.

## Features

- **FastAPI** with automatic Swagger documentation at `/`
- **WebSocket support** for real-time events (`/ws`, `/ws/{cog_name}`)
- **Per-cog error isolation** - cog failures return 503, don't crash server
- **Structured logging** with rotation per cog
- **Health monitoring** - track cog status and system health
- **Configuration system** - YAML config with environment overrides

## Quick Start

1. **Install dependencies** (extends existing ../pyreqs.txt):
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```bash
   python3 flowy_unified_api.py
   ```

3. **Access the API**:
   - Swagger UI: http://localhost:8000/
   - System health: http://localhost:8000/health
   - Cog list: http://localhost:8000/cogs

## API Structure

### Main Endpoints
- `GET /` - Swagger UI documentation
- `GET /health` - System health + all cog status
- `GET /cogs` - List all loaded cogs and capabilities
- `WS /ws` - Main WebSocket (multiplexed events)
- `WS /ws/{cog_name}` - Cog-specific WebSocket

### Cog Endpoints

#### LED Control (`/led/*`)
- `GET /led/status` - LED strip status
- `GET /led/pixel/{id}` - Get pixel color
- `POST /led/pixel` - Set pixel color
- `POST /led/fill` - Fill all pixels
- `POST /led/clear` - Turn off all LEDs

#### NFC Operations (`/nfc/*`)
- `GET /nfc/ping` - Check NFC availability
- `POST /nfc/enable` - Start polling for tags
- `POST /nfc/write` - Write text to tag
- `WS /ws/nfc` - Real-time tag events

#### WiFi Management (`/wifi/*`)
- `GET /wifi/interfaces` - List WiFi interfaces
- `GET /wifi/scan` - Scan for networks
- `GET /wifi/current` - Current connection info
- `POST /wifi/connect` - Connect to network
- `POST /wifi/disconnect` - Disconnect from network

#### System Monitoring (`/system/*`)
- `GET /system/info` - Basic system information
- `GET /system/resources` - CPU, memory, disk usage
- `GET /system/processes` - Top processes by CPU
- `GET /system/services` - Systemd service status
- `WS /ws/system` - Real-time system metrics

## Configuration

Edit `config.yaml` to customize:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

cogs:
  led:
    enabled: true
    mock_mode: false  # Set true for testing without hardware
  
  nfc:
    enabled: true
    mock_mode: false
    use_pico_bridge: false
  
  wifi:
    enabled: true
    mock_mode: false
```

### Environment Variables
- `FLOWY_HOST` - Server host
- `FLOWY_PORT` - Server port
- `FLOWY_DEBUG` - Enable debug mode
- `FLOWY_LED_MOCK` - Enable LED mock mode
- `FLOWY_NFC_MOCK` - Enable NFC mock mode
- `FLOWY_WIFI_MOCK` - Enable WiFi mock mode

## Development

### Adding New Cogs

1. Create `cogs/your_cog.py`:
```python
from base_cog import BaseCog

class YourCog(BaseCog):
    async def initialize(self) -> bool:
        # Initialize your hardware/service
        return True
    
    def get_capabilities(self) -> List[str]:
        return ["your_capability"]
    
    async def shutdown(self):
        # Cleanup
        pass
```

2. Register endpoints in `__init__`:
```python
@self.router.get("/your-endpoint")
async def your_endpoint():
    return {"message": "Hello from your cog"}
```

### WebSocket Support

Enable WebSocket in your cog:
```python
def __init__(self, name: str = "your_cog"):
    super().__init__(name)
    self.supports_websocket = True

# Broadcast events to WebSocket clients
await self.broadcast_websocket_event("your_event", {"data": "value"})
```

## Architecture

```
flowy_unified_api.py    # Main server
├── cogs/
│   ├── base_cog.py     # Abstract base class
│   ├── led_cog.py      # LED control
│   ├── nfc_cog.py      # NFC with WebSocket
│   ├── wifi_cog.py     # WiFi management
│   └── system_cog.py   # System monitoring
├── config.yaml         # Configuration
└── config_loader.py    # Config management
```

Each cog runs independently with its own:
- Error handling and logging
- Health monitoring
- WebSocket connections (optional)
- Configuration section

## Systemd Service

A systemd service file is provided for production deployment:
- Service file: `flowy-unified-api.service`
- Includes watchdog, resource limits, and security settings
- Automatic restart on failure
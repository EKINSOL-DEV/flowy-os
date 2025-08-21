"""
Configuration Loader for Flowy Unified API

Loads configuration from YAML file and environment variables.
Provides default values and validation for all configuration options.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    title: str = "Flowy Unified API"
    description: str = "Unified API system for Flowy OS with modular cogs architecture"
    version: str = "1.0.0"

@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "/flowy/logs"
    max_file_size_mb: int = 10
    backup_count: int = 5
    console_logging: bool = True

@dataclass
class CORSConfig:
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: List[str] = field(default_factory=lambda: ["*"])
    allow_headers: List[str] = field(default_factory=lambda: ["*"])

@dataclass
class LEDCogConfig:
    enabled: bool = True
    mock_mode: bool = False
    default_brightness: float = 1.0
    startup_color: str = "purple"

@dataclass
class NFCHardwarePins:
    i2c_bus: str = "/dev/i2c-1"
    gpio_int: int = 23
    gpio_enable: int = 24
    gpio_fwdnld: int = 25

@dataclass
class NFCPolling:
    auto_start: bool = False

@dataclass
class NFCCogConfig:
    enabled: bool = True
    mock_mode: bool = False
    use_pico_bridge: bool = False
    usb_device: Optional[str] = None
    hardware_pins: NFCHardwarePins = field(default_factory=NFCHardwarePins)
    polling: NFCPolling = field(default_factory=NFCPolling)

@dataclass
class WiFiCogConfig:
    enabled: bool = True
    mock_mode: bool = False
    default_interface: str = "wlan0"
    scan_timeout: int = 10
    connection_timeout: int = 30
    prefer_networkmanager: bool = True

@dataclass
class SystemMonitoring:
    update_interval: int = 5
    cache_duration: int = 2
    max_processes: int = 10

@dataclass
class SystemCogConfig:
    enabled: bool = True
    monitoring: SystemMonitoring = field(default_factory=SystemMonitoring)
    allowed_services: List[str] = field(default_factory=lambda: [
        "flowy-unified-api", "NetworkManager", "ssh"
    ])

@dataclass
class CogsConfig:
    led: LEDCogConfig = field(default_factory=LEDCogConfig)
    nfc: NFCCogConfig = field(default_factory=NFCCogConfig)
    wifi: WiFiCogConfig = field(default_factory=WiFiCogConfig)
    system: SystemCogConfig = field(default_factory=SystemCogConfig)

@dataclass
class WebSocketConfig:
    ping_interval: int = 30
    ping_timeout: int = 10
    close_timeout: int = 10

@dataclass
class HealthConfig:
    check_interval: int = 60
    failure_threshold: int = 3

@dataclass
class RateLimiting:
    enabled: bool = False
    requests_per_minute: int = 100

@dataclass
class SecurityConfig:
    api_key_required: bool = False
    api_key_header: str = "X-API-Key"
    allowed_ips: List[str] = field(default_factory=list)
    rate_limiting: RateLimiting = field(default_factory=RateLimiting)

@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    cogs: CogsConfig = field(default_factory=CogsConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

class ConfigLoader:
    """Loads and validates configuration from YAML and environment variables"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self.config = Config()
    
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations"""
        possible_locations = [
            "config.yaml",
            "config.yml", 
            "/etc/flowy/unified-api/config.yaml",
            "/flowy/config/unified-api.yaml",
            os.path.join(os.path.dirname(__file__), "config.yaml")
        ]
        
        for location in possible_locations:
            if os.path.exists(location):
                return location
        
        return None
    
    def load(self) -> Config:
        """Load configuration from file and environment variables"""
        # Load from YAML file if it exists
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    yaml_data = yaml.safe_load(f)
                    self._apply_yaml_config(yaml_data)
                print(f"Configuration loaded from: {self.config_file}")
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        else:
            print("No config file found, using defaults")
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        # Validate configuration
        self._validate_config()
        
        return self.config
    
    def _apply_yaml_config(self, yaml_data: Dict[str, Any]):
        """Apply configuration from YAML data"""
        if not yaml_data:
            return
        
        # Server configuration
        if 'server' in yaml_data:
            server_data = yaml_data['server']
            if isinstance(server_data, dict):
                for key, value in server_data.items():
                    if hasattr(self.config.server, key):
                        setattr(self.config.server, key, value)
        
        # Logging configuration
        if 'logging' in yaml_data:
            logging_data = yaml_data['logging']
            if isinstance(logging_data, dict):
                for key, value in logging_data.items():
                    if hasattr(self.config.logging, key):
                        setattr(self.config.logging, key, value)
        
        # CORS configuration
        if 'cors' in yaml_data:
            cors_data = yaml_data['cors']
            if isinstance(cors_data, dict):
                for key, value in cors_data.items():
                    if hasattr(self.config.cors, key):
                        setattr(self.config.cors, key, value)
        
        # Cogs configuration
        if 'cogs' in yaml_data:
            cogs_data = yaml_data['cogs']
            if isinstance(cogs_data, dict):
                self._apply_cogs_config(cogs_data)
        
        # WebSocket configuration
        if 'websocket' in yaml_data:
            ws_data = yaml_data['websocket']
            if isinstance(ws_data, dict):
                for key, value in ws_data.items():
                    if hasattr(self.config.websocket, key):
                        setattr(self.config.websocket, key, value)
        
        # Health configuration
        if 'health' in yaml_data:
            health_data = yaml_data['health']
            if isinstance(health_data, dict):
                for key, value in health_data.items():
                    if hasattr(self.config.health, key):
                        setattr(self.config.health, key, value)
        
        # Security configuration
        if 'security' in yaml_data:
            security_data = yaml_data['security']
            if isinstance(security_data, dict):
                self._apply_security_config(security_data)
    
    def _apply_cogs_config(self, cogs_data: Dict[str, Any]):
        """Apply cog-specific configuration"""
        # LED cog
        if 'led' in cogs_data and isinstance(cogs_data['led'], dict):
            led_data = cogs_data['led']
            for key, value in led_data.items():
                if hasattr(self.config.cogs.led, key):
                    setattr(self.config.cogs.led, key, value)
        
        # NFC cog
        if 'nfc' in cogs_data and isinstance(cogs_data['nfc'], dict):
            nfc_data = cogs_data['nfc']
            for key, value in nfc_data.items():
                if key == 'hardware_pins' and isinstance(value, dict):
                    for pin_key, pin_value in value.items():
                        if hasattr(self.config.cogs.nfc.hardware_pins, pin_key):
                            setattr(self.config.cogs.nfc.hardware_pins, pin_key, pin_value)
                elif key == 'polling' and isinstance(value, dict):
                    for poll_key, poll_value in value.items():
                        if hasattr(self.config.cogs.nfc.polling, poll_key):
                            setattr(self.config.cogs.nfc.polling, poll_key, poll_value)
                elif hasattr(self.config.cogs.nfc, key):
                    setattr(self.config.cogs.nfc, key, value)
        
        # WiFi cog
        if 'wifi' in cogs_data and isinstance(cogs_data['wifi'], dict):
            wifi_data = cogs_data['wifi']
            for key, value in wifi_data.items():
                if hasattr(self.config.cogs.wifi, key):
                    setattr(self.config.cogs.wifi, key, value)
        
        # System cog
        if 'system' in cogs_data and isinstance(cogs_data['system'], dict):
            system_data = cogs_data['system']
            for key, value in system_data.items():
                if key == 'monitoring' and isinstance(value, dict):
                    for mon_key, mon_value in value.items():
                        if hasattr(self.config.cogs.system.monitoring, mon_key):
                            setattr(self.config.cogs.system.monitoring, mon_key, mon_value)
                elif hasattr(self.config.cogs.system, key):
                    setattr(self.config.cogs.system, key, value)
    
    def _apply_security_config(self, security_data: Dict[str, Any]):
        """Apply security configuration"""
        for key, value in security_data.items():
            if key == 'rate_limiting' and isinstance(value, dict):
                for rate_key, rate_value in value.items():
                    if hasattr(self.config.security.rate_limiting, rate_key):
                        setattr(self.config.security.rate_limiting, rate_key, rate_value)
            elif hasattr(self.config.security, key):
                setattr(self.config.security, key, value)
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Server settings
        if os.getenv('FLOWY_HOST'):
            self.config.server.host = os.getenv('FLOWY_HOST')
        if os.getenv('FLOWY_PORT'):
            try:
                self.config.server.port = int(os.getenv('FLOWY_PORT'))
            except ValueError:
                pass
        if os.getenv('FLOWY_DEBUG'):
            self.config.server.debug = os.getenv('FLOWY_DEBUG').lower() in ('true', '1', 'yes')
        
        # Logging settings
        if os.getenv('FLOWY_LOG_LEVEL'):
            self.config.logging.level = os.getenv('FLOWY_LOG_LEVEL').upper()
        if os.getenv('FLOWY_LOG_DIR'):
            self.config.logging.log_dir = os.getenv('FLOWY_LOG_DIR')
        
        # Cog overrides
        if os.getenv('FLOWY_LED_MOCK'):
            self.config.cogs.led.mock_mode = os.getenv('FLOWY_LED_MOCK').lower() in ('true', '1', 'yes')
        if os.getenv('FLOWY_NFC_MOCK'):
            self.config.cogs.nfc.mock_mode = os.getenv('FLOWY_NFC_MOCK').lower() in ('true', '1', 'yes')
        if os.getenv('FLOWY_NFC_USB'):
            self.config.cogs.nfc.use_pico_bridge = os.getenv('FLOWY_NFC_USB').lower() in ('true', '1', 'yes')
        if os.getenv('FLOWY_WIFI_MOCK'):
            self.config.cogs.wifi.mock_mode = os.getenv('FLOWY_WIFI_MOCK').lower() in ('true', '1', 'yes')
        
        # NFC hardware settings
        if os.getenv('NFC_I2C_BUS'):
            self.config.cogs.nfc.hardware_pins.i2c_bus = os.getenv('NFC_I2C_BUS')
        if os.getenv('NFC_PIN_INT'):
            try:
                self.config.cogs.nfc.hardware_pins.gpio_int = int(os.getenv('NFC_PIN_INT'))
            except ValueError:
                pass
        if os.getenv('NFC_PIN_ENABLE'):
            try:
                self.config.cogs.nfc.hardware_pins.gpio_enable = int(os.getenv('NFC_PIN_ENABLE'))
            except ValueError:
                pass
        if os.getenv('NFC_PIN_FWDNLD'):
            try:
                self.config.cogs.nfc.hardware_pins.gpio_fwdnld = int(os.getenv('NFC_PIN_FWDNLD'))
            except ValueError:
                pass
    
    def _validate_config(self):
        """Validate configuration values"""
        # Validate server port
        if not (1 <= self.config.server.port <= 65535):
            raise ValueError(f"Invalid port number: {self.config.server.port}")
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.logging.level not in valid_levels:
            raise ValueError(f"Invalid log level: {self.config.logging.level}")
        
        # Validate LED brightness
        if not (0.0 <= self.config.cogs.led.default_brightness <= 1.0):
            raise ValueError(f"Invalid LED brightness: {self.config.cogs.led.default_brightness}")
        
        # Validate GPIO pin numbers
        nfc_pins = self.config.cogs.nfc.hardware_pins
        for pin_name, pin_value in [
            ('gpio_int', nfc_pins.gpio_int),
            ('gpio_enable', nfc_pins.gpio_enable), 
            ('gpio_fwdnld', nfc_pins.gpio_fwdnld)
        ]:
            if not (0 <= pin_value <= 40):  # Raspberry Pi GPIO range
                raise ValueError(f"Invalid NFC {pin_name}: {pin_value}")
        
        # Validate timeouts
        if self.config.cogs.wifi.scan_timeout <= 0:
            raise ValueError(f"Invalid WiFi scan timeout: {self.config.cogs.wifi.scan_timeout}")
        if self.config.cogs.wifi.connection_timeout <= 0:
            raise ValueError(f"Invalid WiFi connection timeout: {self.config.cogs.wifi.connection_timeout}")
        
        print("Configuration validation passed")

# Global config instance
_config_loader = ConfigLoader()
CONFIG = _config_loader.load()

def get_config() -> Config:
    """Get the current configuration"""
    return CONFIG

def reload_config(config_file: Optional[str] = None) -> Config:
    """Reload configuration from file"""
    global CONFIG, _config_loader
    _config_loader = ConfigLoader(config_file)
    CONFIG = _config_loader.load()
    return CONFIG
"""
WiFi Cog for Flowy Unified API

Provides endpoints for WiFi management including scanning, connecting, and status monitoring.
Converted from the original WiFi API to use the cogs architecture.
"""

import sys
import os
from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException, Query, Body
from pydantic import BaseModel

# Add the modules path for imports  
modules_path = os.path.join(os.path.dirname(__file__), "../modules")
sys.path.insert(0, modules_path)

try:
    from flowy_wifi_lib import (
        get_interfaces,
        get_ethernet_interfaces,
        get_all_interfaces,
        get_interface,
        get_interface_status,
        get_interface_details,
        get_ethernet_details,
        scan_wifi,
        get_all_networks,
        get_current_wifi,
        connect_wifi,
        connect_wifi_networkmanager,
        disconnect_wifi_networkmanager
    )
    WIFI_LIB_AVAILABLE = True
except ImportError as e:
    print(f"WiFi library not available: {e}")
    WIFI_LIB_AVAILABLE = False

from .base_cog import BaseCog

# Pydantic models
class NetworkScanResult(BaseModel):
    ssid: str
    bssid: str
    frequency: Optional[int] = None
    signal_level: Optional[int] = None
    security: Optional[str] = None

class InterfaceStatus(BaseModel):
    name: str
    type: str  # "wifi" or "ethernet"
    status: str
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    connected_ssid: Optional[str] = None

class ConnectRequest(BaseModel):
    ssid: str
    password: str
    interface_name: str

class DisconnectRequest(BaseModel):
    interface_name: str

class WiFiCog(BaseCog):
    """WiFi management cog for network operations"""
    
    def __init__(self, name: str = "wifi"):
        super().__init__(name)
        
        # Register WiFi endpoints
        self._register_wifi_endpoints()
    
    async def initialize(self) -> bool:
        """Initialize WiFi functionality"""
        try:
            if WIFI_LIB_AVAILABLE:
                # Test basic functionality
                interfaces = get_interfaces()
                self.logger.info(f"WiFi library initialized, found interfaces: {interfaces}")
                self.status = "running"
                return True
            else:
                self.logger.warning("WiFi library not available, using mock functionality")
                self.status = "running"  # Still run but with limited functionality
                return True
        except Exception as e:
            self.log_error(e, "WiFi initialization failed")
            self.status = "degraded"
            return True  # Continue running even if some functionality is limited
    
    async def shutdown(self):
        """Clean shutdown of WiFi functionality"""
        try:
            self.logger.info("WiFi cog shutting down")
            # No specific cleanup needed for WiFi operations
        except Exception as e:
            self.log_error(e, "WiFi shutdown error")
    
    def get_capabilities(self) -> List[str]:
        """Return WiFi capabilities"""
        capabilities = [
            "wifi_management",
            "network_scanning",
            "connection_control",
            "interface_monitoring",
            "status_reporting"
        ]
        
        if WIFI_LIB_AVAILABLE:
            capabilities.extend([
                "hardware_control",
                "networkmanager_integration",
                "wpa_supplicant_fallback",
                "ethernet_support"
            ])
        else:
            capabilities.extend([
                "mock_control",
                "limited_functionality"
            ])
        
        return capabilities
    
    def _check_wifi_available(self):
        """Check if WiFi library is available"""
        if not WIFI_LIB_AVAILABLE:
            raise HTTPException(status_code=503, detail="WiFi library not available")
    
    def _mock_interfaces(self) -> List[Dict[str, Any]]:
        """Mock interface data for testing"""
        return [
            {"name": "wlan0", "status": "connected", "type": "wifi"},
            {"name": "eth0", "status": "disconnected", "type": "ethernet"}
        ]
    
    def _mock_networks(self) -> List[Dict[str, Any]]:
        """Mock network scan data for testing"""
        return [
            {
                "ssid": "MockNetwork1",
                "bssid": "aa:bb:cc:dd:ee:ff",
                "frequency": 2437,
                "signal_level": -45,
                "security": "WPA2"
            },
            {
                "ssid": "MockNetwork2", 
                "bssid": "11:22:33:44:55:66",
                "frequency": 5180,
                "signal_level": -62,
                "security": "WPA3"
            }
        ]
    
    def _register_wifi_endpoints(self):
        """Register all WiFi-specific endpoints"""
        
        @self.router.get("/interfaces")
        async def get_interfaces_endpoint():
            """Get all available wireless interfaces with their status"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    return self._mock_interfaces()
                
                interface_names = get_interfaces()
                self.logger.info(f"Found interface names: {interface_names}")
                
                iface_list = []
                for name in interface_names:
                    try:
                        iface = get_interface(name)
                        if iface:
                            status = get_interface_status(iface)
                            iface_list.append({
                                "name": name,
                                "status": status,
                                "type": "wifi"
                            })
                            iface.disconnect()
                        else:
                            self.logger.warning(f"Could not get interface object for: {name}")
                    except Exception as e:
                        self.logger.error(f"Error processing interface {name}: {str(e)}")
                        iface_list.append({
                            "name": name,
                            "status": f"ERROR: {str(e)}",
                            "type": "wifi"
                        })
                
                return iface_list
            except Exception as e:
                self.log_error(e, "Error getting interfaces")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/interfaces/ethernet")
        async def get_ethernet_interfaces_endpoint():
            """Get all available ethernet interfaces with their status"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    return [{"name": "eth0", "status": "disconnected", "type": "ethernet"}]
                
                interface_names = get_ethernet_interfaces()
                self.logger.info(f"Found ethernet interface names: {interface_names}")
                
                iface_list = []
                for name in interface_names:
                    try:
                        details = get_ethernet_details(name)
                        iface_list.append({
                            "name": name,
                            "type": "ethernet",
                            "status": details.get("status", "Unknown"),
                            "ip_address": details.get("ip_address"),
                            "mac_address": details.get("mac_address"),
                            "speed": details.get("speed"),
                            "duplex": details.get("duplex"),
                            "link_detected": details.get("link_detected", False)
                        })
                    except Exception as e:
                        self.logger.error(f"Error processing ethernet interface {name}: {str(e)}")
                        iface_list.append({
                            "name": name,
                            "type": "ethernet",
                            "status": f"ERROR: {str(e)}"
                        })
                
                return iface_list
            except Exception as e:
                self.log_error(e, "Error getting ethernet interfaces")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/interfaces/all")
        async def get_all_interfaces_endpoint():
            """Get both wireless and ethernet interfaces"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    return {
                        "wifi": [{"name": "wlan0", "status": "connected", "type": "wifi"}],
                        "ethernet": [{"name": "eth0", "status": "disconnected", "type": "ethernet"}]
                    }
                
                # Get WiFi interfaces
                wifi_interfaces = []
                wifi_names = get_interfaces()
                for name in wifi_names:
                    try:
                        iface = get_interface(name)
                        if iface:
                            status = get_interface_status(iface)
                            wifi_interfaces.append({
                                "name": name,
                                "type": "wifi",
                                "status": status
                            })
                            iface.disconnect()
                    except Exception as e:
                        wifi_interfaces.append({
                            "name": name,
                            "type": "wifi",
                            "status": f"ERROR: {str(e)}"
                        })
                
                # Get Ethernet interfaces
                ethernet_interfaces = []
                ethernet_names = get_ethernet_interfaces()
                for name in ethernet_names:
                    try:
                        details = get_ethernet_details(name)
                        ethernet_interfaces.append({
                            "name": name,
                            "type": "ethernet",
                            "status": details.get("status", "Unknown"),
                            "link_detected": details.get("link_detected", False)
                        })
                    except Exception as e:
                        ethernet_interfaces.append({
                            "name": name,
                            "type": "ethernet",
                            "status": f"ERROR: {str(e)}"
                        })
                
                return {
                    "wifi": wifi_interfaces,
                    "ethernet": ethernet_interfaces
                }
            except Exception as e:
                self.log_error(e, "Error getting all interfaces")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/interface")
        async def get_interface_endpoint(
            interface_name: str = Query(..., description="Name of the interface")):
            """Get detailed information for a specific interface"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    return {
                        "name": interface_name,
                        "type": "wifi" if "wlan" in interface_name else "ethernet",
                        "status": "connected" if "wlan0" == interface_name else "disconnected",
                        "ip_address": "192.168.1.100" if "wlan0" == interface_name else None,
                        "mac_address": "aa:bb:cc:dd:ee:ff"
                    }
                
                # First check if it's an ethernet interface
                ethernet_interfaces = get_ethernet_interfaces()
                if interface_name in ethernet_interfaces:
                    details = get_ethernet_details(interface_name)
                    return {
                        "name": details.get("name", interface_name),
                        "type": "ethernet",
                        "status": details.get("status", "Unknown"),
                        "ip_address": details.get("ip_address"),
                        "mac_address": details.get("mac_address"),
                        "speed": details.get("speed"),
                        "duplex": details.get("duplex"),
                        "link_detected": details.get("link_detected", False)
                    }
                
                # Check WiFi interface
                iface = get_interface(interface_name)
                if iface:
                    full_details = get_interface_details(iface)
                    iface.disconnect()
                    
                    return {
                        "name": full_details.get("name", interface_name),
                        "type": "wifi",
                        "status": full_details.get("status", "Unknown"),
                        "ip_address": full_details.get("ip_address"),
                        "mac_address": full_details.get("mac_address"),
                        "connected_ssid": full_details.get("ssid")
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Interface {interface_name} not found")
                    
            except Exception as e:
                self.log_error(e, f"Error getting interface details for {interface_name}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/scan")
        async def scan_networks_endpoint(
            interface_name: str = Query(..., description="Interface to scan with")):
            """Scan for available WiFi networks"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    return self._mock_networks()
                
                self.logger.info(f"Scanning Wi-Fi networks on interface: {interface_name}")
                networks = scan_wifi(interface_name)
                return networks
            except Exception as e:
                self.log_error(e, f"Error scanning networks on {interface_name}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/networks")
        async def get_all_networks_endpoint(
            interface_name: str = Query(..., description="Interface to list networks from")):
            """Get all discovered networks (without deduplication)"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    return self._mock_networks()
                
                self.logger.info(f"Getting all networks for interface: {interface_name}")
                networks = get_all_networks(interface_name)
                return networks
            except Exception as e:
                self.log_error(e, f"Error getting all networks for {interface_name}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/current")
        async def get_current_network_endpoint(
            interface_name: str = Query("wlan0", description="Interface to check")):
            """Get information about the currently connected network"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    return {
                        "connected": True,
                        "ssid": "MockNetwork1",
                        "bssid": "aa:bb:cc:dd:ee:ff",
                        "frequency": 2437,
                        "signal": -45,
                        "security": "WPA2"
                    }
                
                self.logger.info(f"Getting current network details for interface: {interface_name}")
                
                # Skip get_current_wifi() since it times out - go directly to interface details
                # which uses NetworkManager and works properly
                iface = get_interface(interface_name)
                if not iface:
                    self.logger.info(f"Interface {interface_name} not found")
                    return {"connected": False, "ssid": None}
                
                details = get_interface_details(iface)
                iface.disconnect()
                
                # Check if interface is connected to WiFi
                if details.get("status") != "Connected" or not details.get("connected_ssid"):
                    self.logger.info(f"Interface {interface_name} not connected to WiFi")
                    return {"connected": False, "ssid": None}
                
                # Return current network info in the expected format
                return {
                    "connected": True,
                    "ssid": details.get("connected_ssid"),
                    "bssid": details.get("bssid", ""),
                    "frequency": details.get("frequency", ""),
                    "signal": details.get("signal_level", 0),
                    "security": details.get("security", "WPA/WPA2")
                }
                    
            except Exception as e:
                self.log_error(e, "Error getting current network")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/connect")
        async def connect_network_endpoint(request: ConnectRequest):
            """Connect to a WiFi network"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    self.logger.info(f"Mock connect to {request.ssid} on {request.interface_name}")
                    return {"connected": True, "message": f"Mock connected to {request.ssid}"}
                
                self.logger.info(f"Attempting to connect to {request.ssid} on {request.interface_name}")
                
                # Use NetworkManager as primary method
                result = connect_wifi_networkmanager(request.ssid, request.password, request.interface_name)
                
                if not result:
                    self.logger.info("NetworkManager connection failed, trying wpa_supplicant as fallback...")
                    result = connect_wifi(request.ssid, request.password, request.interface_name)
                
                self.logger.info(f"Connection result: {result}")
                
                if result:
                    return {
                        "connected": True,
                        "message": f"Successfully connected to {request.ssid}"
                    }
                else:
                    return {
                        "connected": False,
                        "message": f"Failed to connect to {request.ssid}"
                    }
            except Exception as e:
                self.log_error(e, f"Error connecting to {request.ssid}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/disconnect")
        async def disconnect_network_endpoint(request: DisconnectRequest):
            """Disconnect from the current WiFi network"""
            try:
                if not WIFI_LIB_AVAILABLE:
                    self.logger.info(f"Mock disconnect from {request.interface_name}")
                    return {"disconnected": True, "message": f"Mock disconnected from {request.interface_name}"}
                
                self.logger.info(f"Attempting to disconnect from WiFi on {request.interface_name}")
                
                # Use NetworkManager
                result = disconnect_wifi_networkmanager(request.interface_name)
                
                self.logger.info(f"Disconnection result: {result}")
                
                if result:
                    return {
                        "disconnected": True,
                        "message": f"Successfully disconnected from {request.interface_name}"
                    }
                else:
                    return {
                        "disconnected": False,
                        "message": f"Failed to disconnect from {request.interface_name}"
                    }
            except Exception as e:
                self.log_error(e, f"Error disconnecting from {request.interface_name}")
                raise HTTPException(status_code=500, detail=str(e))

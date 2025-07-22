import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware  # Optional: only needed if CORS is required
from fastapi.staticfiles import StaticFiles
from flowy_wifi_lib import (
    get_interfaces,
    get_interface,
    get_interface_status,
    get_interface_details,
    scan_wifi,
    get_all_networks,
    get_current_wifi,
    connect_wifi,
    connect_wifi_networkmanager,
    disconnect_wifi_networkmanager
)

PORT = 10_000

# Create logs directory if it doesn't exist
log_dir = '/flowy/logs/wifi'
os.makedirs(log_dir, exist_ok=True)

# Set up logging
log_file = os.path.join(log_dir, 'wifi_api.log')
handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)  # 10MB per log file
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger("wifi_api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Initialize FastAPI app with metadata for automatic Swagger docs and offline assets
app = FastAPI(
    title="Flowy Wi-Fi API",
    description="API to manage and query Wi-Fi interfaces using flowy_wifi_lib",
    version="1.0.0",
    swagger_ui_parameters={"deepLinking": False},
    swagger_js_url="/static/swagger-ui-bundle.js",
    swagger_css_url="/static/swagger-ui.css",
    redoc_url=None  # Disable ReDoc to use only Swagger UI
)

# Create static directory for Swagger UI assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Enable CORS for local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins. You can replace "*" with specific origins if needed.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/interfaces", summary="Get All Interfaces",
         description="Retrieve all available wireless interfaces on the device with their status.")
def get_interfaces_endpoint():
    logger.info("Retrieving all wireless interfaces")
    try:
        interface_names = get_interfaces()
        logger.info(f"Found interface names: {interface_names}")
        
        # Transform the interface names into a JSON serializable format with status
        iface_list = []
        for name in interface_names:
            logger.info(f"Processing interface: {name}")
            try:
                iface = get_interface(name)
                if iface:
                    logger.info(f"Getting status for interface: {name}")
                    status = get_interface_status(iface)
                    logger.info(f"Status for {name}: {status}")
                    iface_list.append({
                        "name": name,
                        "status": status
                    })
                    iface.disconnect()  # Ensure connection is closed
                else:
                    logger.warning(f"Could not get interface object for: {name}")
            except Exception as e:
                logger.error(f"Error processing interface {name}: {str(e)}")
                iface_list.append({
                    "name": name,
                    "status": f"ERROR: {str(e)}"
                })
        
        logger.info(f"Returning interface list: {iface_list}")
        return iface_list
    except Exception as e:
        logger.error(f"Error in get_interfaces_endpoint: {str(e)}")
        return {"error": str(e)}


@app.get("/interface", summary="Get Interface Details", 
         description="Retrieve pure interface details like IP address, MAC address, and connection status.")
def get_interface_endpoint(
        interface_name: str = Query(..., description="Name of the interface to retrieve information for")):
    logger.info(f"Getting interface details for: {interface_name}")
    iface = get_interface(interface_name)
    if iface:
        try:
            # Get full details but filter to interface-only data
            full_details = get_interface_details(iface)
            iface.disconnect()
            
            # Return only interface-specific data
            interface_data = {
                "name": full_details.get("name", interface_name),
                "status": full_details.get("status", "Unknown"),
                "ip_address": full_details.get("ip_address"),
                "mac_address": full_details.get("mac_address")
            }
            
            return interface_data
        except Exception as e:
            logger.error(f"Error getting interface details: {e}")
            return {"error": f"Failed to get interface details: {str(e)}"}
    else:
        return {"error": f"Interface {interface_name} not found"}


# New Network-focused endpoints
@app.get("/network/scan", summary="Scan Wi-Fi Networks",
         description="Scan for available Wi-Fi networks on a given interface and return a deduplicated list.")
def network_scan_endpoint(
        interface_name: str = Query(..., description="Name of the interface to perform the Wi-Fi scan on")):
    logger.info(f"Scanning Wi-Fi networks on interface: {interface_name}")
    networks = scan_wifi(interface_name)
    return networks

# Legacy endpoint for backward compatibility
@app.get("/scan_wifi", deprecated=True, summary="[DEPRECATED] Scan Wi-Fi Networks",
         description="[DEPRECATED] Use /network/scan instead. Scan for available Wi-Fi networks on a given interface.")
def scan_wifi_endpoint(
        interface_name: str = Query(..., description="Name of the interface to perform the Wi-Fi scan on")):
    logger.info(f"[DEPRECATED] Scanning Wi-Fi networks on interface: {interface_name}")
    networks = scan_wifi(interface_name)
    return networks


@app.get("/networks", summary="Get All Networks",
         description="List all Wi-Fi networks discovered on a given interface (without deduplication).")
def get_all_networks_endpoint(
        interface_name: str = Query(..., description="Name of the interface to list networks from")):
    logger.info(f"Getting all networks for interface: {interface_name}")
    networks = get_all_networks(interface_name)
    return networks


@app.get("/network/current", summary="Get Current Network",
         description="Get detailed information about the currently connected Wi-Fi network.")
def network_current_endpoint(
        interface_name: str = Query("wlan0", description="Name of the interface to check for current network")):
    logger.info(f"Getting current network details for interface: {interface_name}")
    
    # Get basic current wifi info
    current = get_current_wifi()
    if not current or not current.get('ssid'):
        return {"connected": False, "ssid": None}
    
    # Enrich with interface details if connected
    try:
        iface = get_interface(interface_name)
        if iface:
            full_details = get_interface_details(iface)
            iface.disconnect()
            
            # Return network-specific data
            if full_details.get("ssid") == current.get("ssid"):
                network_data = {
                    "connected": True,
                    "ssid": full_details.get("ssid"),
                    "bssid": full_details.get("bssid"),
                    "frequency": full_details.get("frequency"),
                    "signal_level": full_details.get("signal_level"),
                    "security": "WPA/WPA2"  # Default assumption
                }
                return network_data
    except Exception as e:
        logger.error(f"Error getting network details: {e}")
    
    # Fallback to basic info
    return {"connected": True, "ssid": current.get("ssid")}

# Legacy endpoint for backward compatibility
@app.get("/current_wifi", deprecated=True, summary="[DEPRECATED] Get Current Wi-Fi",
         description="[DEPRECATED] Use /network/current instead. Get information about the currently connected Wi-Fi network.")
def get_current_wifi_endpoint():
    logger.info("[DEPRECATED] Getting currently connected Wi-Fi")
    current = get_current_wifi()
    return current


@app.post("/network/connect", summary="Connect to Network",
          description="Connect to a Wi-Fi network with the given SSID and password on a specified interface.")
def network_connect_endpoint(
        ssid: str = Body(..., description="SSID of the Wi-Fi network to connect to"),
        password: str = Body(..., description="Password for the Wi-Fi network"),
        interface_name: str = Body(..., description="Name of the interface to use for the connection")
):
    logger.info(f"Attempting to connect to Wi-Fi network {ssid} on interface {interface_name}")
    
    # Use NetworkManager as primary method
    result = connect_wifi_networkmanager(ssid, password, interface_name)
    
    if not result:
        logger.info("NetworkManager connection failed, trying wpa_supplicant as fallback...")
        result = connect_wifi(ssid, password, interface_name)
    
    logger.info(f"Connection result: {result}")
    return {"connected": result}

# Legacy endpoint for backward compatibility
@app.post("/connect_wifi", deprecated=True, summary="[DEPRECATED] Connect to Wi-Fi",
          description="[DEPRECATED] Use /network/connect instead. Connect to a Wi-Fi network with the given SSID and password.")
def connect_wifi_endpoint(
        ssid: str = Body(..., description="SSID of the Wi-Fi network to connect to"),
        password: str = Body(..., description="Password for the Wi-Fi network"),
        interface_name: str = Body(..., description="Name of the interface to use for the connection")
):
    logger.info(f"[DEPRECATED] Attempting to connect to Wi-Fi network {ssid} on interface {interface_name}")
    
    # Use NetworkManager as primary method
    result = connect_wifi_networkmanager(ssid, password, interface_name)
    
    if not result:
        logger.info("NetworkManager connection failed, trying wpa_supplicant as fallback...")
        result = connect_wifi(ssid, password, interface_name)
    
    logger.info(f"Connection result: {result}")
    return {"connected": result}


@app.post("/network/disconnect", summary="Disconnect from Network",
          description="Disconnect from the currently connected WiFi network on a specified interface.")
def network_disconnect_endpoint(
        interface_name: str = Body(..., description="Name of the interface to disconnect from the network")
):
    logger.info(f"Attempting to disconnect from WiFi network on interface {interface_name}")
    
    # Use NetworkManager as primary method
    result = disconnect_wifi_networkmanager(interface_name)
    
    logger.info(f"Disconnection result: {result}")
    return {"disconnected": result}

# Legacy endpoint for backward compatibility
@app.post("/disconnect_wifi", deprecated=True, summary="[DEPRECATED] Disconnect from WiFi",
          description="[DEPRECATED] Use /network/disconnect instead. Disconnect from the currently connected WiFi network.")
def disconnect_wifi_endpoint(
        interface_name: str = Body(..., description="Name of the interface to disconnect from the network")
):
    logger.info(f"[DEPRECATED] Attempting to disconnect from WiFi network on interface {interface_name}")
    
    # Use NetworkManager as primary method
    result = disconnect_wifi_networkmanager(interface_name)
    
    logger.info(f"Disconnection result: {result}")
    return {"disconnected": result}


if __name__ == "__main__":
    import uvicorn
    import os

    is_development = os.getenv("ENVIRONMENT", "production") == "development"
    logger.info(f"WiFi Server is listening to port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=is_development)
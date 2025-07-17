import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware  # Optional: only needed if CORS is required
from flowy_wifi_lib import (
    get_interfaces,
    get_interface,
    get_interface_status,
    get_interface_details,
    scan_wifi,
    get_all_networks,
    get_current_wifi,
    connect_wifi
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

# Initialize FastAPI app with metadata for automatic Swagger docs
app = FastAPI(
    title="Flowy Wi-Fi API",
    description="API to manage and query Wi-Fi interfaces using flowy_wifi_lib",
    version="1.0.0"
)

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
         description="Retrieve comprehensive details of a network interface including status, IP address, connected network info, etc.")
def get_interface_endpoint(
        interface_name: str = Query(..., description="Name of the interface to retrieve information for")):
    logger.info(f"Getting interface details for: {interface_name}")
    iface = get_interface(interface_name)
    if iface:
        try:
            details = get_interface_details(iface)
            iface.disconnect()
            return details
        except Exception as e:
            logger.error(f"Error getting interface details: {e}")
            return {"error": f"Failed to get interface details: {str(e)}"}
    else:
        return {"error": f"Interface {interface_name} not found"}


@app.get("/scan_wifi", summary="Scan Wi-Fi Networks",
         description="Scan for available Wi-Fi networks on a given interface and return a deduplicated list.")
def scan_wifi_endpoint(
        interface_name: str = Query(..., description="Name of the interface to perform the Wi-Fi scan on")):
    logger.info(f"Scanning Wi-Fi networks on interface: {interface_name}")
    networks = scan_wifi(interface_name)
    return networks


@app.get("/networks", summary="Get All Networks",
         description="List all Wi-Fi networks discovered on a given interface (without deduplication).")
def get_all_networks_endpoint(
        interface_name: str = Query(..., description="Name of the interface to list networks from")):
    logger.info(f"Getting all networks for interface: {interface_name}")
    networks = get_all_networks(interface_name)
    return networks


@app.get("/current_wifi", summary="Get Current Wi-Fi",
         description="Get information about the currently connected Wi-Fi network.")
def get_current_wifi_endpoint():
    logger.info("Getting currently connected Wi-Fi")
    current = get_current_wifi()
    return current


@app.post("/connect_wifi", summary="Connect to Wi-Fi",
          description="Connect to a Wi-Fi network with the given SSID and password on a specified interface.")
def connect_wifi_endpoint(
        ssid: str = Body(..., description="SSID of the Wi-Fi network to connect to"),
        password: str = Body(..., description="Password for the Wi-Fi network"),
        interface_name: str = Body(..., description="Name of the interface to use for the connection")
):
    logger.info(f"Attempting to connect to Wi-Fi network {ssid} on interface {interface_name}")
    result = connect_wifi(ssid, password, interface_name)
    logger.info(f"Connection result: {result}")
    return {"connected": result}


if __name__ == "__main__":
    import uvicorn
    import os

    is_development = os.getenv("ENVIRONMENT", "production") == "development"
    logger.info(f"WiFi Server is listening to port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=is_development)
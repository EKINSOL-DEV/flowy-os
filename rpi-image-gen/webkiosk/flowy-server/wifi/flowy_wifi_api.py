import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware  # Optional: only needed if CORS is required
from flowy_wifi_lib import (
    get_interfaces,
    get_interface,
    get_interface_status,
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
    interfaces = get_interfaces()
    # Transform the interface objects into a JSON serializable format
    iface_list = []
    for iface in interfaces:
        iface_list.append({
            "name": iface.name(),
            "status": get_interface_status(iface)
        })
    return iface_list


@app.get("/interface", summary="Get Interface Details", description="Retrieve details of a network interface by name.")
def get_interface_endpoint(
        interface_name: str = Query(..., description="Name of the interface to retrieve information for")):
    logger.info(f"Getting interface details for: {interface_name}")
    iface_details = get_interface(interface_name)
    return iface_details


@app.get("/interface_status", summary="Get Interface Status",
         description="Get the status of a network interface by name.")
def get_interface_status_endpoint(
        interface_name: str = Query(..., description="Name of the interface to check status for")):
    logger.info(f"Getting interface status for: {interface_name}")
    iface = get_interface(interface_name)
    status = get_interface_status(iface)
    return {"interface": iface.name(), "status": status}


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

    logger.info(f"WiFi Server is listening to port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=True)
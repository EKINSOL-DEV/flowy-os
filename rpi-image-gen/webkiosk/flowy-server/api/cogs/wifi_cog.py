\
"""
WiFi Cog: exposes endpoints exactly as specified in endpoints.json (WIFI section).
Does not use BaseCog. It captures import errors and function-missing cases and returns
HTTP errors without crashing the app.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any, Dict

router = APIRouter(tags=["WIFI"])

# Import the underlying library
try:
    import flowy_wifi_lib as wifi
except Exception as e:
    wifi = None
    _wifi_import_error = e
else:
    _wifi_import_error = None

def _require_wifi():
    if wifi is None:
        raise HTTPException(status_code=500, detail=f"Failed to import flowy_wifi_lib: {_wifi_import_error}")

def _call(func_name: str, *args, **kwargs):
    _require_wifi()
    fn = getattr(wifi, func_name, None)
    if fn is None:
        raise HTTPException(status_code=501, detail=f"{func_name} is not implemented in flowy_wifi_lib")
    try:
        return fn(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ConnectRequest(BaseModel):
    ssid: str
    password: str
    interface_name: str

class DisconnectRequest(BaseModel):
    interface_name: str

# --------- Endpoints (matching endpoints.json) ----------

@router.get("/wifi/interfaces", summary="Get Interfaces Endpoint", description="Get all available wireless interfaces with their status")
def get_interfaces():
    # Prefer wifi.get_interfaces(); fall back to get_all_interfaces filtered, if needed
    return _call("get_interfaces")

@router.get("/wifi/interfaces/ethernet", summary="Get Ethernet Interfaces Endpoint", description="Get all available ethernet interfaces with their status")
def get_ethernet_interfaces():
    return _call("get_ethernet_interfaces")

@router.get("/wifi/interfaces/all", summary="Get All Interfaces Endpoint", description="Get both wireless and ethernet interfaces")
def get_all_interfaces():
    return _call("get_all_interfaces")

@router.get("/wifi/interface", summary="Get Interface Endpoint", description="Get detailed information for a specific interface")
def get_interface(interface_name: str = Query(..., description="Name of the interface")):
    _require_wifi()
    # Try the most specific functions first
    if interface_name.startswith("eth") and hasattr(wifi, "get_ethernet_details"):
        return _call("get_ethernet_details", interface_name)
    # Prefer NetworkManager-specific if present
    if hasattr(wifi, "get_interface_details_networkmanager"):
        try:
            return _call("get_interface_details_networkmanager", interface_name)
        except HTTPException:
            raise
        except Exception:
            # fall through to generic details
            pass
    if hasattr(wifi, "get_interface_details"):
        return _call("get_interface_details", interface_name)
    if hasattr(wifi, "get_interface"):
        return _call("get_interface", interface_name)
    raise HTTPException(status_code=501, detail="No interface detail function available")

@router.get("/wifi/scan", summary="Scan Networks Endpoint", description="Scan for available WiFi networks")
def scan_networks(interface_name: str = Query(..., description="Interface to scan with")):
    # Prefer NM scan, then generic scan
    if hasattr(wifi, "scan_wifi_networkmanager"):
        return _call("scan_wifi_networkmanager", interface_name)
    if hasattr(wifi, "scan_wifi"):
        return _call("scan_wifi", interface_name)
    raise HTTPException(status_code=501, detail="scan_wifi_networkmanager/scan_wifi not implemented")

@router.get("/wifi/networks", summary="Get All Networks Endpoint", description="Get all discovered networks (without deduplication)")
def get_all_networks(interface_name: str = Query(..., description="Interface to list networks from")):
    return _call("get_all_networks", interface_name)

@router.get("/wifi/current", summary="Get Current Network Endpoint", description="Get information about the currently connected network")
def get_current(interface_name: Optional[str] = Query("wlan0", description="Interface to check")):
    # Some implementations ignore the parameter; pass if supported
    _require_wifi()
    if hasattr(wifi, "get_current_wifi"):
        try:
            # get_current_wifi() in your lib takes no arguments; call without
            return wifi.get_current_wifi()
        except TypeError:
            # just in case an alternate signature exists
            return _call("get_current_wifi", interface_name)
    raise HTTPException(status_code=501, detail="get_current_wifi not implemented")

@router.post("/wifi/connect", summary="Connect Network Endpoint", description="Connect to a WiFi network")
def connect_network(req: ConnectRequest):
    # Prefer NetworkManager path
    if hasattr(wifi, "connect_wifi_networkmanager"):
        ok = _call("connect_wifi_networkmanager", req.ssid, req.password, req.interface_name)
        return {"success": bool(ok)}
    if hasattr(wifi, "connect_wifi"):
        ok = _call("connect_wifi", req.ssid, req.password, req.interface_name)
        return {"success": bool(ok)}
    raise HTTPException(status_code=501, detail="connect_wifi_networkmanager/connect_wifi not implemented")

@router.post("/wifi/disconnect", summary="Disconnect Network Endpoint", description="Disconnect from the current WiFi network")
def disconnect_network(req: DisconnectRequest):
    # Prefer NetworkManager path; not all libs implement a generic disconnect
    if hasattr(wifi, "disconnect_wifi_networkmanager"):
        ok = _call("disconnect_wifi_networkmanager", req.interface_name)
        return {"success": bool(ok)}
    # If a generic disconnect exists, try it
    if hasattr(wifi, "disconnect_wifi"):
        ok = _call("disconnect_wifi", req.interface_name)
        return {"success": bool(ok)}
    raise HTTPException(status_code=501, detail="disconnect_wifi_networkmanager/disconnect_wifi not implemented")

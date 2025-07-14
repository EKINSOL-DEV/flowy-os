import subprocess
import time
import pywifi
from pywifi import const

def get_interfaces():
    """
    Retrieve all wireless interfaces on the device.

    Returns:
        list: A list of pywifi.interfaces.Interface objects.
    """
    wifi = pywifi.PyWiFi()
    interfaces = wifi.interfaces()
    if not interfaces:
        print("No wireless interfaces found.")
        return []
    return interfaces

def get_interface(interface_name="wlan0"):
    """
    Retrieve the wireless interface matching the specified name.

    Args:
        interface_name (str): The name of the interface to use (default is "wlan0").

    Returns:
        pywifi.interfaces.Interface: The matching wireless interface, or the first available interface if not found.
    """
    wifi = pywifi.PyWiFi()
    interfaces = wifi.interfaces()
    if not interfaces:
        print("No wireless interfaces found.")
        return None
    for iface in interfaces:
        if iface.name() == interface_name:
            return iface
    print(f"Interface '{interface_name}' not found. Using interface: {interfaces[0].name()}")
    return interfaces[0]


def get_interface_status(iface):
    """
    Get a human-readable string representing the status of the given interface.

    Args:
        iface (pywifi.interfaces.Interface): The wireless interface.

    Returns:
        str: A string representation of the interface status (e.g., DISCONNECTED, SCANNING, etc.).
    """
    status_map = {
        const.IFACE_DISCONNECTED: "DISCONNECTED",
        const.IFACE_SCANNING: "SCANNING",
        const.IFACE_INACTIVE: "INACTIVE",
        const.IFACE_CONNECTING: "CONNECTING",
        const.IFACE_CONNECTED: "CONNECTED"
    }
    status_code = iface.status()
    return status_map.get(status_code, f"Unknown ({status_code})")


def scan_wifi(interface_name="wlan0"):
    """
    Scan for available Wi-Fi networks using the specified interface and return a deduplicated list.

    The function deduplicates networks by SSID, keeping only the entry with the strongest signal.

    Args:
        interface_name (str): The name of the interface to use (default is "wlan0").

    Returns:
        list: A list of dictionaries containing network details such as SSID, signal, BSSID, frequency, and authentication info.
    """
    iface = get_interface(interface_name)
    if iface is None:
        return []

    print(f"Using interface: {iface.name()}")
    print(f"Interface Status: {get_interface_status(iface)}")

    iface.scan()  # Start scanning
    time.sleep(5)  # Wait for the scan to complete
    results = iface.scan_results()

    # Deduplicate networks by SSID (keeping the entry with the best signal)
    networks = {}
    for network in results:
        ssid = network.ssid
        if not ssid or ssid.strip() == "" or ssid == "\x00":
            continue

        try:
            signal = int(network.signal)
        except ValueError:
            signal = -100  # Fallback signal strength

        if ssid in networks:
            try:
                existing_signal = int(networks[ssid]['signal'])
            except ValueError:
                existing_signal = -100
            if signal > existing_signal:
                networks[ssid] = {
                    "ssid": ssid,
                    "signal": str(signal),
                    "bssid": network.bssid,
                    "frequency": network.freq,
                    "auth": network.akm
                }
        else:
            networks[ssid] = {
                "ssid": ssid,
                "signal": str(signal),
                "bssid": network.bssid,
                "frequency": network.freq,
                "auth": network.akm
            }
    return list(networks.values())


def get_all_networks(interface_name="wlan0"):
    """
    Scan for available Wi-Fi networks using the specified interface and return all found networks.

    This function returns every scanned network without deduplication.

    Args:
        interface_name (str): The name of the interface to use (default is "wlan0").

    Returns:
        list: A list of dictionaries with details of each network.
    """
    iface = get_interface(interface_name)
    if iface is None:
        return []

    print(f"Using interface: {iface.name()} for full scan.")
    iface.scan()  # Start scanning
    time.sleep(5)  # Wait for the scan to complete
    results = iface.scan_results()

    networks = []
    for network in results:
        networks.append({
            "ssid": network.ssid,
            "signal": str(network.signal),
            "bssid": network.bssid,
            "frequency": network.freq,
            "auth": network.akm
        })
    return networks


def get_current_wifi():
    """
    Retrieve the currently connected Wi-Fi network using nmcli.

    The function runs 'nmcli -t -f active,ssid dev wifi' and returns the first active (yes) network.

    Returns:
        dict or None: A dictionary with the key 'ssid' for the currently connected network, or None if not connected.
    """
    try:
        output = subprocess.check_output(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
            stderr=subprocess.STDOUT
        ).decode("utf-8")
    except subprocess.CalledProcessError as e:
        error_msg = e.output.decode("utf-8") if e.output else "No output available."
        raise Exception(f"Error retrieving current wifi: {error_msg}")

    for line in output.splitlines():
        fields = line.split(':')
        if fields[0].strip() == "yes":
            return {"ssid": fields[1].strip()}
    return None


def connect_wifi(ssid, password, interface_name="wlan0"):
    """
    Connect to a specified Wi-Fi network using the given interface.

    This function creates a new profile (assuming WPA2-PSK security) and attempts to connect.

    Args:
        ssid (str): The SSID of the network to connect to.
        password (str): The password for the network.
        interface_name (str): The interface to use (default is "wlan0").

    Returns:
        bool: True if connected successfully, False otherwise.
    """
    iface = get_interface(interface_name)
    if iface is None:
        return False

    print(f"Using interface: {iface.name()} for connection.")
    print(f"Interface Status before connecting: {get_interface_status(iface)}")

    # Disconnect if already connected
    iface.disconnect()
    time.sleep(1)

    # Remove all existing network profiles (optional but helps avoid conflicts)
    iface.remove_all_network_profiles()

    # Create a new Wi-Fi profile (assumes WPA2-PSK security)
    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.auth = const.AUTH_ALG_OPEN
    profile.akm.append(const.AKM_TYPE_WPA2PSK)
    profile.cipher = const.CIPHER_TYPE_CCMP
    profile.key = password

    tmp_profile = iface.add_network_profile(profile)

    # Initiate connection using the created profile
    iface.connect(tmp_profile)
    print(f"Attempting to connect to '{ssid}' ...")
    time.sleep(5)  # Wait for the connection to be established

    if iface.status() == const.IFACE_CONNECTED:
        print("Connected to Wi-Fi network:", ssid)
        return True
    else:
        print("Failed to connect to Wi-Fi network:", ssid)
        return False


if __name__ == "__main__":
    # For testing purposes when running flowy_wifi_lib.py directly
    default_interface = "wlan0"

    # Test scanning (deduplicated)
    networks = scan_wifi(default_interface)
    if networks:
        print("\nAvailable Wi-Fi Networks (deduplicated):")
        for net in networks:
            print(f"SSID: {net['ssid']}, Signal: {net['signal']}")
    else:
        print("\nNo networks found.")

    # Test getting all networks
    all_networks = get_all_networks(default_interface)
    if all_networks:
        print("\nAll Scanned Wi-Fi Networks:")
        for net in all_networks:
            print(f"SSID: {net['ssid']}, Signal: {net['signal']}")
    else:
        print("\nNo networks found in full scan.")

    # Test current Wi-Fi connection
    current = get_current_wifi()
    if current:
        print("\nCurrently connected Wi-Fi:")
        print(f"SSID: {current['ssid']}")
    else:
        print("\nNot connected to any Wi-Fi network.")

    # Test connecting to a network (uncomment and update with real credentials)
    # ssid_to_connect = "YourSSID"
    # password = "YourPassword"
    # connect_wifi(ssid_to_connect, password, default_interface)
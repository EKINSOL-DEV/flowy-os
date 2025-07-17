import subprocess
import time
import socket
import os
import re

WPA_SUPPLICANT_SOCKET = "/var/run/wpa_supplicant"

class WpaSupplicantInterface:
    """Direct interface to wpa_supplicant control socket."""
    
    def __init__(self, interface_name):
        self.interface_name = interface_name
        self.socket_path = f"{WPA_SUPPLICANT_SOCKET}/{interface_name}"
        self.sock = None
    
    def connect(self):
        """Connect to wpa_supplicant control socket."""
        if not os.path.exists(self.socket_path):
            raise Exception(f"wpa_supplicant socket not found: {self.socket_path}")
        
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.connect(self.socket_path)
        
        # Attach to receive unsolicited messages
        self.send_command("ATTACH")
    
    def disconnect(self):
        """Disconnect from wpa_supplicant control socket."""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def send_command(self, command):
        """Send command to wpa_supplicant and return response."""
        if not self.sock:
            self.connect()
        
        self.sock.send(command.encode())
        response = self.sock.recv(4096).decode().strip()
        return response
    
    def name(self):
        """Get interface name."""
        return self.interface_name

def get_interfaces():
    """
    Retrieve all wireless interfaces on the device.

    Returns:
        list: A list of interface names.
    """
    try:
        # Get wireless interfaces from /proc/net/wireless
        with open('/proc/net/wireless', 'r') as f:
            lines = f.readlines()[2:]  # Skip header lines
            interfaces = []
            for line in lines:
                interface_name = line.split(':')[0].strip()
                interfaces.append(interface_name)
            return interfaces
    except FileNotFoundError:
        print("No wireless interfaces found.")
        return []

def get_interface(interface_name="wlan0"):
    """
    Retrieve the wireless interface matching the specified name.

    Args:
        interface_name (str): The name of the interface to use (default is "wlan0").

    Returns:
        WpaSupplicantInterface: The matching wireless interface, or the first available interface if not found.
    """
    interfaces = get_interfaces()
    if not interfaces:
        print("No wireless interfaces found.")
        return None
    
    if interface_name in interfaces:
        return WpaSupplicantInterface(interface_name)
    
    print(f"Interface '{interface_name}' not found. Using interface: {interfaces[0]}")
    return WpaSupplicantInterface(interfaces[0])

def get_interface_status(iface):
    """
    Get a human-readable string representing the status of the given interface.

    Args:
        iface (WpaSupplicantInterface): The wireless interface.

    Returns:
        str: A string representation of the interface status.
    """
    try:
        response = iface.send_command("STATUS")
        
        # Parse wpa_state from status response
        for line in response.split('\n'):
            if line.startswith('wpa_state='):
                state = line.split('=')[1]
                return state.upper()
        
        return "UNKNOWN"
    except Exception as e:
        return f"ERROR: {str(e)}"

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

    try:
        print(f"Using interface: {iface.name()}")
        print(f"Interface Status: {get_interface_status(iface)}")

        # Trigger scan
        iface.send_command("SCAN")
        time.sleep(3)  # Wait for scan to complete
        
        # Get scan results
        results = iface.send_command("SCAN_RESULTS")
        
        # Parse scan results
        networks = {}
        lines = results.split('\n')[1:]  # Skip header
        
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) < 5:
                continue
                
            bssid = parts[0]
            frequency = parts[1]
            signal = int(parts[2])
            flags = parts[3]
            ssid = parts[4] if len(parts) > 4 else ""
            
            if not ssid or ssid.strip() == "":
                continue
                
            # Deduplicate by SSID, keeping strongest signal
            if ssid in networks:
                if signal > int(networks[ssid]['signal']):
                    networks[ssid] = {
                        "ssid": ssid,
                        "signal": str(signal),
                        "bssid": bssid,
                        "frequency": frequency,
                        "auth": flags
                    }
            else:
                networks[ssid] = {
                    "ssid": ssid,
                    "signal": str(signal),
                    "bssid": bssid,
                    "frequency": frequency,
                    "auth": flags
                }
        
        return list(networks.values())
        
    except Exception as e:
        print(f"Error scanning WiFi: {e}")
        return []
    finally:
        iface.disconnect()

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

    try:
        print(f"Using interface: {iface.name()} for full scan.")
        
        # Trigger scan
        iface.send_command("SCAN")
        time.sleep(3)  # Wait for scan to complete
        
        # Get scan results
        results = iface.send_command("SCAN_RESULTS")
        
        # Parse scan results
        networks = []
        lines = results.split('\n')[1:]  # Skip header
        
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) < 5:
                continue
                
            bssid = parts[0]
            frequency = parts[1]
            signal = parts[2]
            flags = parts[3]
            ssid = parts[4] if len(parts) > 4 else ""
            
            networks.append({
                "ssid": ssid,
                "signal": signal,
                "bssid": bssid,
                "frequency": frequency,
                "auth": flags
            })
        
        return networks
        
    except Exception as e:
        print(f"Error scanning WiFi: {e}")
        return []
    finally:
        iface.disconnect()


def get_current_wifi():
    """
    Retrieve the currently connected Wi-Fi network using wpa_supplicant.

    Returns:
        dict or None: A dictionary with the key 'ssid' for the currently connected network, or None if not connected.
    """
    interfaces = get_interfaces()
    
    for interface_name in interfaces:
        iface = get_interface(interface_name)
        if iface is None:
            continue
            
        try:
            status = iface.send_command("STATUS")
            
            # Parse status response for connected network
            ssid = None
            wpa_state = None
            
            for line in status.split('\n'):
                if line.startswith('ssid='):
                    ssid = line.split('=', 1)[1]
                elif line.startswith('wpa_state='):
                    wpa_state = line.split('=')[1]
            
            if wpa_state == 'COMPLETED' and ssid:
                return {"ssid": ssid}
                
        except Exception as e:
            print(f"Error getting current wifi for {interface_name}: {e}")
        finally:
            iface.disconnect()
    
    return None

def connect_wifi(ssid, password, interface_name="wlan0"):
    """
    Connect to a specified Wi-Fi network using wpa_supplicant.

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

    try:
        print(f"Using interface: {iface.name()} for connection.")
        print(f"Interface Status before connecting: {get_interface_status(iface)}")

        # Disconnect current connection
        iface.send_command("DISCONNECT")
        time.sleep(1)

        # Remove all existing networks
        networks = iface.send_command("LIST_NETWORKS")
        for line in networks.split('\n')[1:]:  # Skip header
            if line.strip():
                network_id = line.split('\t')[0]
                iface.send_command(f"REMOVE_NETWORK {network_id}")

        # Add new network
        response = iface.send_command("ADD_NETWORK")
        network_id = response.strip()
        
        if not network_id.isdigit():
            print(f"Failed to add network: {response}")
            return False

        # Configure network
        commands = [
            f'SET_NETWORK {network_id} ssid "{ssid}"',
            f'SET_NETWORK {network_id} psk "{password}"',
            f'ENABLE_NETWORK {network_id}',
            f'SELECT_NETWORK {network_id}'
        ]
        
        for cmd in commands:
            response = iface.send_command(cmd)
            if response.strip() != "OK":
                print(f"Command failed: {cmd} -> {response}")
                return False

        # Wait for connection
        print(f"Attempting to connect to '{ssid}' ...")
        
        # Check connection status
        for i in range(10):  # Check for up to 10 seconds
            time.sleep(1)
            status = iface.send_command("STATUS")
            
            for line in status.split('\n'):
                if line.startswith('wpa_state='):
                    state = line.split('=')[1]
                    if state == 'COMPLETED':
                        print("Connected to Wi-Fi network:", ssid)
                        return True
                    elif state in ['DISCONNECTED', 'INACTIVE']:
                        print("Connection failed")
                        return False
        
        print("Connection timeout")
        return False
        
    except Exception as e:
        print(f"Error connecting to WiFi: {e}")
        return False
    finally:
        iface.disconnect()


if __name__ == "__main__":
    # For testing purposes when running flowy_wifi_lib.py directly
    default_interface = "wlan0"

    # Test interfaces
    interfaces = get_interfaces()
    print(f"Available interfaces: {interfaces}")

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
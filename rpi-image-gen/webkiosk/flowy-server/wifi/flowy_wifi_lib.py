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
        self.client_socket_path = None
    
    def connect(self):
        """Connect to wpa_supplicant control socket using proper pattern."""
        if not os.path.exists(self.socket_path):
            raise Exception(f"wpa_supplicant socket not found: {self.socket_path}")
        
        # Create single socket for both sending and receiving
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.settimeout(3.0)  # Set 3 second timeout
        
        # Create temporary socket file for this client
        import tempfile
        self.client_socket_path = tempfile.mktemp(prefix="wpa_client_", suffix=".sock")
        
        # Bind to client socket path (required for wpa_supplicant responses)
        self.sock.bind(self.client_socket_path)
    
    def disconnect(self):
        """Disconnect from wpa_supplicant control socket."""
        if self.sock:
            self.sock.close()
            self.sock = None
        if hasattr(self, 'client_socket_path') and self.client_socket_path and os.path.exists(self.client_socket_path):
            os.unlink(self.client_socket_path)
            self.client_socket_path = None
    
    def send_command(self, command):
        """Send command to wpa_supplicant and return response."""
        if not self.sock:
            self.connect()
        
        try:
            # Send command to wpa_supplicant control socket
            self.sock.sendto(command.encode(), self.socket_path)
            # Receive response on the same socket
            response_bytes, _ = self.sock.recvfrom(4096)
            response = response_bytes.decode().strip()
            return response
        except socket.timeout:
            raise Exception(f"Command timed out: {command}")
        except Exception as e:
            raise Exception(f"Command failed: {command} - {str(e)}")
    
    def name(self):
        """Get interface name."""
        return self.interface_name

def get_ethernet_interfaces():
    """
    Retrieve all ethernet interfaces on the device using NetworkManager.

    Returns:
        list: A list of ethernet interface names.
    """
    try:
        result = subprocess.run(['nmcli', '--terse', '--fields', 'DEVICE,TYPE', 'device', 'status'], 
                              capture_output=True, text=True)
        
        ethernet_interfaces = []
        for line in result.stdout.split('\n'):
            if line.strip():
                parts = line.split(':')
                if len(parts) >= 2 and parts[1] == 'ethernet':
                    ethernet_interfaces.append(parts[0])
        
        return ethernet_interfaces
    except Exception as e:
        print(f"Error getting ethernet interfaces: {e}")
        return []

def get_all_interfaces():
    """
    Retrieve both wireless and ethernet interfaces on the device.

    Returns:
        dict: A dictionary with 'wifi' and 'ethernet' keys containing interface lists.
    """
    return {
        'wifi': get_interfaces(),
        'ethernet': get_ethernet_interfaces()
    }

def get_interfaces():
    """
    Retrieve all wireless interfaces on the device.

    Returns:
        list: A list of interface names.
    """
    try:
        # First try to get interfaces from wpa_supplicant global socket
        global_socket = f"{WPA_SUPPLICANT_SOCKET}/global"
        if os.path.exists(global_socket):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                sock.connect(global_socket)
                sock.send(b"INTERFACES")
                response = sock.recv(4096).decode().strip()
                sock.close()
                
                interfaces = []
                for line in response.split('\n'):
                    if line.strip():
                        # Format: interface_name\tctrl_interface_path
                        parts = line.split('\t')
                        if parts:
                            interfaces.append(parts[0])
                return interfaces
            except Exception as e:
                print(f"Error querying wpa_supplicant global socket: {e}")
        
        # Fallback: check for socket files in wpa_supplicant directory
        if os.path.exists(WPA_SUPPLICANT_SOCKET):
            interfaces = []
            for item in os.listdir(WPA_SUPPLICANT_SOCKET):
                item_path = os.path.join(WPA_SUPPLICANT_SOCKET, item)
                # Check for socket files (not regular files) and exclude special entries
                if os.path.exists(item_path) and item != "global" and not item.startswith("p2p-dev-"):
                    interfaces.append(item)
            return interfaces
        
        # Final fallback: use NetworkManager or ip command to find wireless interfaces
        try:
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if 'wlan' in line or 'wlp' in line:
                    # Extract interface name from ip link output
                    parts = line.split(':')
                    if len(parts) >= 2:
                        iface_name = parts[1].strip().split('@')[0]
                        interfaces.append(iface_name)
            return interfaces
        except Exception as e:
            print(f"Error using ip command: {e}")
            
        return []
        
    except Exception as e:
        print(f"Error getting interfaces: {e}")
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

def get_interface_details_networkmanager(interface_name):
    """
    Get detailed information about the interface using NetworkManager.

    Args:
        interface_name (str): The name of the interface.

    Returns:
        dict: A dictionary with interface details including status, IP, SSID, etc.
    """
    details = {
        "name": interface_name,
        "status": "Disconnected",
        "ip_address": None,
        "ssid": None,
        "bssid": None,
        "frequency": None,
        "signal_level": None
    }
    
    try:
        # Get device information from NetworkManager
        result = subprocess.run(['nmcli', 'device', 'show', interface_name], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'GENERAL.STATE:' in line:
                    state_parts = line.split()
                    if len(state_parts) >= 2:
                        state_num = state_parts[1]
                        if '100' in state_num:
                            details["status"] = "Connected"
                        elif '30' in state_num:
                            details["status"] = "Disconnected"
                        elif '20' in state_num:
                            details["status"] = "Unavailable"
                        else:
                            details["status"] = "Unknown"
                            
                elif 'GENERAL.CONNECTION:' in line and '--' not in line:
                    # Extract connection name (SSID)
                    details["ssid"] = line.split(':', 1)[1].strip()
                    
                elif 'IP4.ADDRESS[1]:' in line:
                    ip_info = line.split(':')[1].strip()
                    if '/' in ip_info:
                        details["ip_address"] = ip_info.split('/')[0]
        
        # If connected, get additional details from WiFi scan
        if details["status"] == "Connected" and details["ssid"]:
            try:
                # Get current connection details
                wifi_result = subprocess.run(['nmcli', '--terse', '--fields', 'ACTIVE,SSID,BSSID,FREQ,SIGNAL', 
                                            'device', 'wifi', 'list', 'ifname', interface_name], 
                                           capture_output=True, text=True)
                
                if wifi_result.returncode == 0:
                    for line in wifi_result.stdout.split('\n'):
                        if line.startswith('yes:'):  # Active connection
                            # Split on colons but handle MAC address properly
                            parts = line.split(':')
                            if len(parts) >= 10:  # yes:SSID:MAC1:MAC2:MAC3:MAC4:MAC5:MAC6:FREQ:SIGNAL
                                # Reconstruct BSSID from parts 2-7 and remove escapes
                                details["bssid"] = ':'.join(parts[2:8]).replace('\\:', ':').rstrip('\\')
                                details["frequency"] = parts[8]
                                # Convert signal to dBm if needed
                                signal = parts[9]
                                try:
                                    signal_int = int(signal)
                                    if signal_int > 0:
                                        details["signal_level"] = str(signal_int - 100)
                                    else:
                                        details["signal_level"] = signal
                                except ValueError:
                                    details["signal_level"] = signal
                            break
            except Exception:
                pass  # Additional details are optional
        
        return details
        
    except Exception as e:
        details["status"] = f"ERROR: {str(e)}"
        return details

def get_interface_details(iface):
    """
    Get detailed information about the interface - uses NetworkManager as primary method.
    """
    # Use NetworkManager first
    interface_name = iface.name() if hasattr(iface, 'name') else str(iface)
    details = get_interface_details_networkmanager(interface_name)
    
    # If NetworkManager doesn't show connection but wpa_supplicant does, fall back
    if details["status"] == "Disconnected":
        try:
            response = iface.send_command("STATUS")
            
            # Parse all status information
            for line in response.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key == 'wpa_state':
                        # Map wpa_supplicant states to more user-friendly names
                        state_map = {
                            'COMPLETED': 'Connected',
                            'DISCONNECTED': 'Disconnected', 
                            'SCANNING': 'Scanning',
                            'ASSOCIATING': 'Connecting',
                            'ASSOCIATED': 'Connecting',
                            'AUTHENTICATING': 'Authenticating',
                            'FOUR_WAY_HANDSHAKE': 'Authenticating',
                            'GROUP_HANDSHAKE': 'Authenticating',
                            'INACTIVE': 'Inactive'
                        }
                        details["status"] = state_map.get(value.upper(), value.upper())
                    elif key == 'ip_address':
                        details["ip_address"] = value
                    elif key == 'ssid':
                        details["ssid"] = value
                    elif key == 'bssid':
                        details["bssid"] = value.replace('\\:', ':').rstrip('\\')
                    elif key == 'freq':
                        details["frequency"] = value
                        
            # Get signal level from scan results if connected
            if details["status"] == "Connected" and details["bssid"]:
                try:
                    scan_response = iface.send_command("SCAN_RESULTS")
                    for line in scan_response.split('\n'):
                        if details["bssid"] in line:
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                details["signal_level"] = parts[2]  # Signal level in dBm
                            break
                except Exception:
                    pass  # Signal level is optional
        except Exception as e:
            if "ERROR:" not in details["status"]:
                details["status"] = f"ERROR: {str(e)}"
        
        return details
    
    return details

def get_ethernet_details(interface_name):
    """
    Get detailed information about an ethernet interface using NetworkManager and ethtool.

    Args:
        interface_name (str): The name of the ethernet interface.

    Returns:
        dict: A dictionary with ethernet interface details.
    """
    details = {
        "name": interface_name,
        "type": "ethernet",
        "status": "Disconnected",
        "ip_address": None,
        "mac_address": None,
        "speed": None,
        "duplex": None,
        "link_detected": False
    }
    
    try:
        # Get basic info from NetworkManager
        result = subprocess.run(['nmcli', 'device', 'show', interface_name], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'GENERAL.STATE:' in line:
                    state_parts = line.split()
                    if len(state_parts) >= 2:
                        state_num = state_parts[1]
                        if '100' in state_num:
                            details["status"] = "Connected"
                        elif '30' in state_num:
                            details["status"] = "Disconnected"
                        elif '20' in state_num:
                            details["status"] = "Unavailable"
                        else:
                            details["status"] = "Unknown"
                            
                elif 'IP4.ADDRESS[1]:' in line:
                    ip_info = line.split(':')[1].strip()
                    if '/' in ip_info:
                        details["ip_address"] = ip_info.split('/')[0]
                        
                elif 'GENERAL.HWADDR:' in line:
                    details["mac_address"] = line.split(':')[1].strip()
        
        # Get physical link status and speed using ethtool
        try:
            ethtool_result = subprocess.run(['ethtool', interface_name], 
                                          capture_output=True, text=True)
            
            if ethtool_result.returncode == 0:
                for line in ethtool_result.stdout.split('\n'):
                    if 'Speed:' in line:
                        details["speed"] = line.split(':')[1].strip()
                    elif 'Duplex:' in line:
                        details["duplex"] = line.split(':')[1].strip()
                    elif 'Link detected:' in line:
                        details["link_detected"] = 'yes' in line.lower()
        except Exception:
            # ethtool might not be available or require sudo
            # Fallback to /sys filesystem
            try:
                with open(f'/sys/class/net/{interface_name}/operstate', 'r') as f:
                    operstate = f.read().strip()
                    details["link_detected"] = operstate == 'up'
            except Exception:
                pass
            
        return details
        
    except Exception as e:
        details["status"] = f"ERROR: {str(e)}"
        return details

def get_interface_status(iface):
    """
    Get a human-readable string representing the status of the given interface.
    
    Args:
        iface (WpaSupplicantInterface): The wireless interface.

    Returns:
        str: A string representation of the interface status.
    """
    details = get_interface_details(iface)
    return details["status"]

def scan_wifi_networkmanager(interface_name="wlan0"):
    """
    Scan for available Wi-Fi networks using NetworkManager and return a deduplicated list.

    Args:
        interface_name (str): The name of the interface to use (default is "wlan0").

    Returns:
        list: A list of dictionaries containing network details such as SSID, signal, BSSID, frequency, and authentication info.
    """
    try:
        print(f"Scanning WiFi networks using NetworkManager on {interface_name}")
        
        # Trigger fresh scan
        subprocess.run(['nmcli', 'device', 'wifi', 'rescan', 'ifname', interface_name], 
                      capture_output=True, text=True)
        time.sleep(2)  # Wait for scan to complete
        
        # Get scan results
        result = subprocess.run(['nmcli', '--terse', '--fields', 'SSID,SIGNAL,BSSID,FREQ,SECURITY', 
                               'device', 'wifi', 'list', 'ifname', interface_name], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"NetworkManager scan failed: {result.stderr}")
            return []
        
        networks = {}
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            # Split carefully - BSSID contains colons, so we need to handle this properly
            parts = line.split(':')
            if len(parts) < 8:  # SSID:SIGNAL:MAC1:MAC2:MAC3:MAC4:MAC5:MAC6:FREQ:SECURITY
                continue
                
            ssid = parts[0].strip()
            signal = parts[1].strip()
            # Reconstruct BSSID from parts 2-7 and remove escapes
            bssid = ':'.join(parts[2:8]).replace('\\:', ':').strip()
            frequency = parts[8].strip() if len(parts) > 8 else ""
            security = parts[9].strip() if len(parts) > 9 else ""
            
            if not ssid or ssid == "--":
                continue
                
            # Convert signal to negative dBm format for consistency
            try:
                signal_int = int(signal)
                if signal_int > 0:
                    signal = str(signal_int - 100)  # Convert percentage to approximate dBm
            except ValueError:
                pass
                
            # Deduplicate by SSID, keeping strongest signal
            if ssid in networks:
                if int(signal) > int(networks[ssid]['signal']):
                    networks[ssid] = {
                        "ssid": ssid,
                        "signal": signal,
                        "bssid": bssid,
                        "frequency": frequency,
                        "auth": security
                    }
            else:
                networks[ssid] = {
                    "ssid": ssid,
                    "signal": signal,
                    "bssid": bssid,
                    "frequency": frequency,
                    "auth": security
                }
        
        return list(networks.values())
        
    except Exception as e:
        print(f"Error scanning WiFi with NetworkManager: {e}")
        return []

def scan_wifi(interface_name="wlan0"):
    """
    Scan for available Wi-Fi networks - uses NetworkManager as primary method.
    """
    # Try NetworkManager first
    networks = scan_wifi_networkmanager(interface_name)
    if networks:
        return networks
    
    # Fallback to wpa_supplicant if NetworkManager fails
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
                
            bssid = parts[0].replace('\\:', ':').rstrip('\\')
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
                
            bssid = parts[0].replace('\\:', ':').rstrip('\\')
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

def connect_wifi_networkmanager(ssid, password, interface_name="wlan0"):
    """
    Connect to a WiFi network using NetworkManager (nmcli).
    
    Args:
        ssid (str): The SSID of the network to connect to.
        password (str): The password for the network.
        interface_name (str): The interface to use (default is "wlan0").
    
    Returns:
        bool: True if connected successfully, False otherwise.
    """
    try:
        print(f"Connecting to '{ssid}' using NetworkManager...")
        
        # First, try to connect directly
        cmd = ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password, 'ifname', interface_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully connected to '{ssid}'")
            
            # Wait a moment for DHCP
            time.sleep(3)
            
            # Check if we got an IP
            status_result = subprocess.run(['nmcli', 'device', 'show', interface_name], 
                                         capture_output=True, text=True)
            if 'IP4.ADDRESS' in status_result.stdout:
                print("IP address assigned successfully")
                return True
            else:
                print("Connected but no IP assigned, trying alternative approach...")
                
                # Try creating a connection profile explicitly
                profile_cmd = ['nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', ssid, 
                             'ifname', interface_name, 'ssid', ssid, 'wifi-sec.key-mgmt', 'wpa-psk', 
                             'wifi-sec.psk', password]
                profile_result = subprocess.run(profile_cmd, capture_output=True, text=True)
                
                if profile_result.returncode == 0:
                    # Activate the profile
                    activate_cmd = ['nmcli', 'connection', 'up', ssid]
                    activate_result = subprocess.run(activate_cmd, capture_output=True, text=True)
                    
                    if activate_result.returncode == 0:
                        print(f"Profile created and activated for '{ssid}'")
                        return True
                
                return False
        else:
            print(f"Failed to connect to '{ssid}': {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error connecting to WiFi via NetworkManager: {e}")
        return False

def disconnect_wifi_networkmanager(interface_name="wlan0"):
    """
    Disconnect from WiFi using NetworkManager.
    
    Args:
        interface_name (str): The interface to disconnect (default is "wlan0").
    
    Returns:
        bool: True if disconnected successfully, False otherwise.
    """
    try:
        print(f"Disconnecting {interface_name} using NetworkManager...")
        
        # Disconnect the device
        cmd = ['nmcli', 'device', 'disconnect', interface_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully disconnected {interface_name}")
            return True
        else:
            print(f"Failed to disconnect {interface_name}: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error disconnecting WiFi via NetworkManager: {e}")
        return False

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
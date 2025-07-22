# Claude Context File

## Development Environment
- **Current system**: HOST OS (Ubuntu/Linux development machine)
- **Target system**: Raspberry Pi (flowpi) - this is where the flowy-os project runs
- **IMPORTANT**: Never run bash commands directly - the user needs to run them on the Pi
- **IMPORTANT**: Always suggest commands for the user to run, don't execute them

## Project Structure
- Working on flowy-os project
- WiFi API server runs on Raspberry Pi
- Main WiFi library: `rpi-image-gen/webkiosk/flowy-server/wifi/flowy_wifi_lib.py`
- WiFi API: `rpi-image-gen/webkiosk/flowy-server/wifi/flowy_wifi_api.py`

## Current Status
- NetworkManager is managing WiFi connections
- wpa_supplicant runs with `-u` flag (D-Bus mode) controlled by NetworkManager
- WiFi connections work but IP assignment (DHCP) is failing
- All endpoints use NetworkManager as primary method with wpa_supplicant fallback

## Key Reminders
1. NEVER use Bash tool - always suggest commands for user to run
2. Host OS ≠ Target Pi - they are different systems. Reminder 1 does not apply if the command is intended for the HOST OS and NOT THE PI.
3. User runs commands on Pi, reports results back
4. Focus on suggesting the right commands, not executing them
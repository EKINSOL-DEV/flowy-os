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
1. **Bash tool usage**: 
   - ✅ USE Bash tool for HOST OS commands (development work, file operations, building, etc.)
   - ✅ USE Bash tool for Pi commands when SSH'd into Pi environment
   - ❌ NEVER use Bash tool to SSH into Pi or run Pi commands from host
   - When in doubt: if you're currently in the target environment, use Bash tool
2. Host OS ≠ Target Pi - they are different systems
3. For Pi operations from host: suggest SSH commands for user to run
4. Focus on using tools appropriately based on current environment
5. NEVER give multi-line Python code in command suggestions - only one-liners allowed (copying from terminal adds extra spaces that break Python indentation)
6. For multi-line Python code, create test files in a debug folder instead
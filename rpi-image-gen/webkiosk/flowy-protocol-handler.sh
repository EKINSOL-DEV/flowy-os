#!/bin/bash
# flowy-protocol-handler.sh - Handle flowy:// protocol URLs

URL="$1"
ACTION="${URL#flowy://}"

case "$ACTION" in
    "disksk")
        # Stop and disable the kiosk service
        sudo systemctl stop flowy-kiosk.service
        sudo systemctl disable flowy-kiosk.service
        
        # Log the action
        logger "flowy-protocol-handler: Stopped and disabled kiosk service"
        
        # Exit chromium to complete the kiosk shutdown
        pkill -f chromium-browser
        ;;
    *)
        logger "flowy-protocol-handler: Unknown action: $ACTION"
        ;;
esac
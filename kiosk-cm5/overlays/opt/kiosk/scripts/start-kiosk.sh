#!/bin/bash
# Kiosk browser startup script

# Wait for services to be ready
sleep 5

# Configure display
export DISPLAY=:0
xset -dpms
xset s off
xset s noblank

# Hide cursor
unclutter -idle 0.1 -root &

# Start chromium in kiosk mode
chromium-browser \
    --kiosk \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-extensions \
    --disable-plugins \
    --disable-translate \
    --disable-infobars \
    --disable-features=TranslateUI \
    --disable-ipc-flooding-protection \
    --noerrdialogs \
    --no-first-run \
    --fast \
    --fast-start \
    --disable-default-apps \
    --disable-popup-blocking \
    --disable-prompt-on-repost \
    --no-message-box \
    --start-fullscreen \
    --app=http://localhost/ &

# Keep script running
wait
#!/bin/bash
# Chromium kiosk mode for Flowy device app.
# Deployed to /usr/bin/flowy-kiosk on the Pi.

# Wait for nginx to be ready on port 8080 before launching Chromium,
# otherwise Chromium opens an error page and stays there.
for i in $(seq 1 30); do
    curl -s -o /dev/null http://localhost:8080 && break
    sleep 1
done

# Use a dedicated profile dir — wiped on each launch to prevent
# session restore and stale cache from overriding the target URL.
KIOSK_PROFILE="/tmp/flowy-chromium-profile"
rm -rf "$KIOSK_PROFILE"

exec chromium-browser \
    --kiosk \
    --user-data-dir="$KIOSK_PROFILE" \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --disable-translate \
    --disable-features=TranslateUI \
    --disable-session-crashed-bubble \
    --disable-application-cache \
    --disk-cache-size=1 \
    --window-size=1280,800 \
    --window-position=0,0 \
    --disable-pinch \
    --overscroll-history-navigation=disabled \
    http://localhost:8080

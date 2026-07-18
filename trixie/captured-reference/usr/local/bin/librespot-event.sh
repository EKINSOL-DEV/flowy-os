#!/bin/bash
# Librespot event handler — writes playback state to a shared location.
# Configured via LIBRESPOT_ONEVENT in /etc/raspotify/conf.
#
# IMPORTANT: Do NOT write to /tmp — raspotify runs with PrivateTmp=true,
# so its /tmp is isolated and invisible to other processes.
STATE_FILE="/run/librespot-state.json"

write_state() {
  echo "$1" > "$STATE_FILE"
  chmod 644 "$STATE_FILE" 2>/dev/null
}

case "$PLAYER_EVENT" in
  playing)
    write_state "{\"playing\":true,\"track_id\":\"$TRACK_ID\",\"duration_ms\":${DURATION_MS:-0},\"position_ms\":${POSITION_MS:-0}}"
    ;;
  paused)
    write_state "{\"playing\":false,\"track_id\":\"$TRACK_ID\",\"duration_ms\":${DURATION_MS:-0},\"position_ms\":${POSITION_MS:-0}}"
    ;;
  stopped)
    write_state "{\"playing\":false,\"track_id\":null}"
    ;;
  changed)
    write_state "{\"playing\":true,\"track_id\":\"$TRACK_ID\",\"duration_ms\":${DURATION_MS:-0},\"position_ms\":0}"
    ;;
esac

#!/bin/bash
# Librespot event handler — writes playback state to JSON for the music cog
STATE_FILE="/tmp/librespot-state.json"

case "$PLAYER_EVENT" in
  playing)
    echo "{\"playing\":true,\"track_id\":\"$TRACK_ID\",\"duration_ms\":$DURATION_MS,\"position_ms\":${POSITION_MS:-0}}" > "$STATE_FILE"
    ;;
  paused)
    echo "{\"playing\":false,\"track_id\":\"$TRACK_ID\",\"duration_ms\":$DURATION_MS,\"position_ms\":${POSITION_MS:-0}}" > "$STATE_FILE"
    ;;
  stopped)
    echo "{\"playing\":false,\"track_id\":null}" > "$STATE_FILE"
    ;;
  changed)
    echo "{\"playing\":true,\"track_id\":\"$TRACK_ID\",\"duration_ms\":$DURATION_MS,\"position_ms\":0}" > "$STATE_FILE"
    ;;
esac

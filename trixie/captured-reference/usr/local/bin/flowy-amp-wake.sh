#!/bin/sh
# /usr/local/bin/flowy-amp-wake.sh — librespot onevent hook (FLOW-347).
#
# The speaker amp (TPA3118) auto-shuts-down after silence to keep the board
# cool. librespot starts playing the moment someone casts from the Spotify app
# (Zeroconf), without passing through the Flowy API, so this hook wakes the amp
# the instant librespot reports a playback event. The server-side ALSA watcher
# is the safety net; this hook just removes the poll latency.
#
# Wired up via LIBRESPOT_ONEVENT in /etc/raspotify/conf.
case "$PLAYER_EVENT" in
  playing|preloading|started|changed)
    curl -s -m 2 -X POST http://127.0.0.1:10000/power/amp/wake >/dev/null 2>&1 || true
    ;;
esac
exit 0

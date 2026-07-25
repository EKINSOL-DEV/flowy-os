#!/bin/bash
# Make the HiFiBerry DAC actually usable before raspotify starts.
#
# Two boot-time problems this guards against:
#
# 1. HALF-REGISTERED CARD (seen after a cold boot, 2026-07-25). The ASoC card
#    registers while the RP1 i2s controller isn't ready yet, so the card shows
#    up in `aplay -l` but every open fails with EINVAL ("unable to open slave"
#    for dmix). Tell-tale: an empty subdevice name in `aplay -l`. Reloading
#    snd_soc_rpi_simple_soundcard rebuilds the DAI link and fixes it. Symptom
#    for the user: Spotify lists albums but "Flowy" is missing as a playback
#    device, because raspotify died on the broken sink.
#
# 2. MISSING SOFTMASTER (FLOW-328). The volume control is an ALSA *softvol*
#    control that only exists once something opens the `default` PCM. Without
#    priming, librespot exits with `Could not find Alsa mixer control`.
#
# Installed at /usr/local/bin/flowy-audio-init.sh and run by
# flowy-audio-init.service (ordered Before=raspotify.service).

CARD="sndrpihifiberry"
log() { echo "flowy-audio-init: $*"; }

# Can we actually open the DAC (not just see it)?
card_opens() {
  aplay -q -D "hw:${CARD},0" -d 1 -f cd /dev/zero 2>/dev/null
}

# Wait for the card to appear at all (module autoload / DT probe).
for _ in $(seq 1 20); do
  aplay -l 2>/dev/null | grep -q "$CARD" && break
  sleep 1
done

# If the card is present but refuses to open, it registered before the i2s
# controller was ready — reload the machine driver to rebuild the DAI link.
if aplay -l 2>/dev/null | grep -q "$CARD" && ! card_opens; then
  log "card present but not openable — reloading soundcard module"
  modprobe -r snd_soc_rpi_simple_soundcard 2>/dev/null
  sleep 1
  modprobe snd_soc_rpi_simple_soundcard 2>/dev/null
  for _ in $(seq 1 10); do
    card_opens && { log "card recovered after module reload"; break; }
    sleep 1
  done
fi

# Prime the softvol control so raspotify finds SoftMaster.
for _ in $(seq 1 15); do
  if aplay -q -D default -d 1 -f cd /dev/zero 2>/dev/null; then
    if amixer scontrols 2>/dev/null | grep -q SoftMaster; then
      log "audio ready (SoftMaster primed)"
      exit 0
    fi
  fi
  sleep 1
done

log "WARNING: audio not fully initialised; raspotify may fail"
exit 0  # never block boot

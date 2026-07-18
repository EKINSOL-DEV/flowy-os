#!/bin/bash
# Prime the ALSA softvol "SoftMaster" control by opening the default PCM once, so
# raspotify (which starts at boot) can find the mixer control. Without this, on a
# fresh boot the softvol control does not exist yet and librespot fails with
# "Could not find Alsa mixer control".
for i in $(seq 1 15); do
  if aplay -q -D default -d 1 -f cd /dev/zero 2>/dev/null; then
    if amixer scontrols 2>/dev/null | grep -q SoftMaster; then exit 0; fi
  fi
  sleep 1
done
exit 0

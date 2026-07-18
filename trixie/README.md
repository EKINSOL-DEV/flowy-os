# flowy-trixie — image-as-code voor de Flowy (FLOW-352/354/358)

Bouwt met de **upstream** [rpi-image-gen](https://github.com/raspberrypi/rpi-image-gen)
(niet de gevendorde oude kopie in de repo-root) een flashklaar
Raspberry Pi OS-achtig image op **Debian trixie** voor de CM5:

- weston 14 (kiosk-shell + desktop-shell browser-modus, text-input-v3 → on-screen keyboard)
- chromium-kiosk via `flowy-kiosk` + weston autolaunch
- FastAPI-server in venv (`/flowy/server`), nginx (companion :80, kiosk :8080)
- raspotify (Spotify Connect) geordend ná `flowy-audio-init` (SoftMaster-prime)
- ALSA dmix/softvol, HiFiBerry DAC, Waveshare 10.1" DSI-paneel, i2c1 (TMP1075), SPI (PN532)
- amp-wake hook, browser-modus switch, `flowy-ui`, updater-script

## Structuur

- `flowy-trixie.yaml` — hoofdconfig (device cm5, image-rpios, lagen)
- `layer/flowy-device.yaml` — de Flowy-laag: packages + customize-hooks
- `overlay/` — 1-op-1 rootfs-bestanden (gecureerd van het referentietoestel)
- `captured-reference/` — ruwe capture van het referentietoestel (2026-07-18,
  bookworm), geheimen gescrubd; alleen ter referentie/diff
- `build.sh` — orkestratie vanaf een dev-machine: bouwt de frontend uit
  `../flowy-app`, staged payloads, synct naar de arm-bouwserver en draait daar
  rpi-image-gen

## Bouwen

```bash
# vereist: ../flowy-app checkout, node 22+, sshpass; server: zie build.sh
trixie/build.sh
```

Artefact: `~/rpi-image-gen/work/image-flowy-trixie/flowy-trixie.img` op de
bouwserver.

## Eerste boot (bewust NIET in het image)

- Spotify: `SPOTIFY_CLIENT_ID`/`SECRET` invullen in
  `/etc/systemd/system/flowy-unified-api.service` (placeholders `__PROVISION_ME__`),
  daarna OAuth-koppeling via de companion
- WiFi-credentials (NetworkManager), parental PIN
- Verificatie-checklist: zie FLOW-358

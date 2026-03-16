# Flowy OS

Raspberry Pi OS image builder for the **Flowy smart clock**. Generates a ready-to-flash SD card image with all hardware drivers, kiosk configuration, and service definitions.

For the application software (frontend, companion app, API server), see [flowy-app](https://github.com/EKINSOL-DEV/flowy-app).

## What This Repo Does

- Builds a minimal Debian-based OS image for Raspberry Pi CM5
- Configures the kiosk browser (Chromium in fullscreen)
- Installs hardware drivers (touchscreen, LED strip, NFC reader, audio)
- Sets up WiFi via NetworkManager
- Configures systemd services for the Flowy API server
- Auto-expands the root filesystem on first boot
- Handles Spotify Connect via librespot

## Structure

```
flowy-os/
├── rpi-image-gen/          Image build system
│   ├── webkiosk/
│   │   ├── flowy-server/   Legacy server directory (moved to flowy-app)
│   │   │   ├── wifi/       WiFi management scripts
│   │   │   ├── nfc/        NFC tools
│   │   │   ├── led/        LED test scripts
│   │   │   └── dial/       Rotary encoder support
│   │   └── services/       Systemd service templates
│   └── ...
├── kiosk-cm5/              CM5-specific overlays and configs
└── ...
```

## Building an Image

See the build system documentation in `rpi-image-gen/` for image generation instructions.

## Related Repos

| Repo | Purpose |
|------|---------|
| [flowy-app](https://github.com/EKINSOL-DEV/flowy-app) | Frontend + Companion PWA + API Server |
| flowy-os (this repo) | OS image builder + hardware configuration |

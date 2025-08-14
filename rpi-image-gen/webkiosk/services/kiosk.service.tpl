[Unit]
Description=Kiosk Wayland Session (labwc)
After=multi-user.target

[Service]
User=<KIOSK_USER>
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=yes
Type=notify

# Private runtime dir for the Wayland socket (0700)
RuntimeDirectory=labwc
RuntimeDirectoryMode=0700
Environment=XDG_RUNTIME_DIR=/run/labwc
# Wayland hint for Electron/Chromium-based apps
Environment=ELECTRON_OZONE_PLATFORM_HINT=wayland

# Start labwc on VT1
ExecStart=/usr/bin/labwc
Restart=always
StandardError=journal

[Install]
WantedBy=default.target

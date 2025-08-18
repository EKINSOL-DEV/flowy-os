[Unit]
Description=Kiosk Wayland Session (Weston)
After=multi-user.target graphical-session-pre.target
Wants=graphical-session-pre.target
Conflicts=getty@tty1.service
After=getty@tty1.service

[Service]
User=<KIOSK_USER>
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=yes
Type=simple
TimeoutStartSec=30
Restart=on-failure
RestartSec=5
StartLimitBurst=3
StartLimitInterval=30

# Private runtime dir for the Wayland socket (0700)
RuntimeDirectory=weston
RuntimeDirectoryMode=0700
Environment=XDG_RUNTIME_DIR=/run/weston
# Graphics environment
Environment=XDG_SESSION_TYPE=wayland
Environment=XDG_SESSION_CLASS=user
# Wayland hint for Electron/Chromium-based apps
Environment=ELECTRON_OZONE_PLATFORM_HINT=wayland

# Start Weston on VT1 and let systemd know when it's ready
ExecStart=/usr/bin/weston --tty=/dev/tty1 --modules=systemd-notify.so
# Comment out labwc for now - seat management issues
# ExecStart=/bin/bash -c '/usr/bin/labwc || WLR_RENDERER=pixman /usr/bin/labwc'
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target

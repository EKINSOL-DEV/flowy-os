[Unit]
Description=Apply Wayland Display Rotation
BindsTo=flowy-kiosk.service
After=flowy-kiosk.service

[Service]
Type=oneshot
User=<KIOSK_USER>
Environment="WAYLAND_DISPLAY=wayland-0"
Environment="XDG_RUNTIME_DIR=/home/<KIOSK_USER>"
ExecStart=/bin/bash -c 'while [ ! -S /home/<KIOSK_USER>/wayland-0 ]; do sleep 1; done; /usr/bin/wlr-randr --output DSI-2 --transform 270'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
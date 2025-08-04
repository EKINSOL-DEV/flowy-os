[Unit]
Description=NFC GPIO Initialization
After=multi-user.target
Before=flowy-nfcserver.service

[Service]
Type=oneshot
User=root
ExecStart=/usr/bin/gpioset gpiochip0 9=1
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
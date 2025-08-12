[Unit]
Description=Flowy NFC Server Session
After=multi-user.target

[Service]
User=root
Restart=always
WorkingDirectory=<SERVER_DIR>/nfc
ExecStart=<PYTHON_EXEC> nfc_api.py --usb-device /dev/ttyACM0
StandardError=journal

[Install]
WantedBy=default.target
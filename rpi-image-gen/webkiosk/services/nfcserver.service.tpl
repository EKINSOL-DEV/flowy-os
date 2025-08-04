[Unit]
Description=Flowy NFC Server Session
After=multi-user.target flowy-nfc-init.service

[Service]
User=root
Restart=always
WorkingDirectory=<SERVER_DIR>
ExecStart=<PYTHON_EXEC> nfc_api.py --i2c-bus /dev/i2c-4 --gpio-int 25 --gpio-enable 9 --gpio-fwdnld 8
StandardError=journal

[Install]
WantedBy=default.target
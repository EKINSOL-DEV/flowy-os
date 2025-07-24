[Unit]
Description=Flowy NFC Server Session
After=multi-user.target

[Service]
User=root
Restart=always
WorkingDirectory=<SERVER_DIR>
ExecStart=<PYTHON_EXEC> nfc_api.py
StandardError=journal

[Install]
WantedBy=default.target
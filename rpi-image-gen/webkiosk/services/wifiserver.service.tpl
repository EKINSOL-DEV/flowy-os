[Unit]
Description=Flowy Server Session
After=multi-user.target

[Service]
User=<KIOSK_USER>
Restart=always
WorkingDirectory=<SERVER_DIR>
ExecStart=<PYTHON_EXEC> flowy_wifi_api.py
StandardError=journal

[Install]
WantedBy=default.target